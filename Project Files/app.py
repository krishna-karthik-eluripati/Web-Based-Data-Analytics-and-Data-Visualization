from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
import io
import os
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

# Make sure to configure a temp folder for large files
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/csv-process')
def index():
    return render_template('csv process.html')

# Route to handle the CSV file upload and processing
@app.route('/process-csv', methods=['POST'])
def process_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename.endswith('.csv'):
        try:
            # Secure the file name and store the file on the server
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Read the CSV file using pandas
            df = pd.read_csv(file_path)

            # Store column names and CSV content in session
            session['columns'] = df.columns.tolist()
            session['csv_file_path'] = file_path  # Store file path in session

            # Example: Let's process and return the number of rows
            processed_output = len(df)
            
            return jsonify({'processed_output': processed_output})
        
        except Exception as e:
            print(f'Error processing CSV: {str(e)}')
            return jsonify({'error': f'Error processing CSV: {str(e)}'}), 400
    
    else:
        return jsonify({'error': 'Only CSV files are allowed'}), 400

# Route for the data analytics page
@app.route('/data-analytics.html', methods=['GET', 'POST'])
def data_analytics():
    columns = session.get('columns', [])
    processed_output = None
    error_message = None

    if request.method == 'POST':
        action = request.form.get('actions')
        column = request.form.get('columns')
        sort_order = request.form.get('sort')
        retrieve = request.form.get('retrieve')
        range_value = request.form.get('range')

        # Load the CSV file from session
        file_path = session.get('csv_file_path')
        if file_path:
            df = pd.read_csv(file_path)

            # Process the CSV based on user inputs
            if action == 'analytics':
                if column and sort_order:
                    if sort_order == 'ascending':
                        df = df.sort_values(by=column, ascending=True)
                    elif sort_order == 'descending':
                        df = df.sort_values(by=column, ascending=False)
                    else:
                        error_message = "Invalid sort order selected."
                else:
                    error_message = "Please select a column and a sort order for analytics."
            elif action == 'summary':
                if retrieve and range_value and range_value.isdigit():
                    range_value = int(range_value)
                    if range_value <= 0:
                        error_message = "Please enter a positive number for the range."
                    else:
                        if retrieve == 'head':
                            df = df.head(range_value)
                        elif retrieve == 'tail':
                            df = df.tail(range_value)
                        
                        if column and sort_order:
                            if sort_order == 'ascending':
                                df = df.sort_values(by=column, ascending=True)
                            elif sort_order == 'descending':
                                df = df.sort_values(by=column, ascending=False)
                            else:
                                error_message = "Invalid sort order selected."
                else:
                    error_message = "Please select a retrieve operation and provide a valid range."
                
            # Convert the processed DataFrame to HTML
            if not error_message:
                processed_output = df.to_html(classes="table table-bordered")
            else:
                processed_output = f"<p style='color:red'>{error_message}</p>"

        else:
            error_message = "No CSV file is loaded. Please upload a file first."

    return render_template('data analytics.html', columns=columns, processed_output=processed_output)

# Route for the data visualization page
@app.route('/data-visualization.html', methods=['GET', 'POST'])
def data_visualization():
    columns = session.get('columns', [])
    processed_output = None
    error_message = None

    if request.method == 'POST':
        visualization_type = request.form.get('visualizations')
        x_axis = request.form.get('x-axis')
        y_axis = request.form.get('y-axis')

        # Load the CSV file from session
        file_path = session.get('csv_file_path')
        if file_path:
            df = pd.read_csv(file_path)

            # Validate if X and Y axis columns are selected appropriately
            if visualization_type in ['bar_chart', 'line_chart', 'scatter_plot', 'box_plot', 'area_chart'] and x_axis and y_axis:
                processed_output = generate_visualization(visualization_type, x_axis, y_axis, df)
            elif visualization_type in ['pie_chart', 'histogram'] and x_axis:
                processed_output = generate_visualization(visualization_type, x_axis, None, df)
            else:
                error_message = "Please select valid visualization options."

        else:
            error_message = "No CSV file is loaded. Please upload a file first."

    return render_template('data visualization.html', columns=columns, processed_output=processed_output, error_message=error_message)


def generate_visualization(visualization_type, x_axis, y_axis, df):
    # Create and return the appropriate visualization based on user selection
    if visualization_type == 'bar_chart' and x_axis and y_axis:
        fig, ax = plt.subplots()
        sns.barplot(x=df[x_axis], y=df[y_axis], ax=ax)
        ax.set_title('Bar Chart')
    elif visualization_type == 'line_chart' and x_axis and y_axis:
        fig, ax = plt.subplots()
        sns.lineplot(x=df[x_axis], y=df[y_axis], ax=ax)
        ax.set_title('Line Chart')
    elif visualization_type == 'pie_chart' and x_axis:
        fig, ax = plt.subplots()
        df[x_axis].value_counts().plot.pie(autopct='%1.1f%%', ax=ax)
        ax.set_title('Pie Chart')
    elif visualization_type == 'scatter_plot' and x_axis and y_axis:
        fig, ax = plt.subplots()
        sns.scatterplot(x=df[x_axis], y=df[y_axis], ax=ax)
        ax.set_title('Scatter Plot')
    elif visualization_type == 'box_plot' and x_axis and y_axis:
        fig, ax = plt.subplots()
        sns.boxplot(x=df[x_axis], y=df[y_axis], ax=ax)
        ax.set_title('Box Plot')
    elif visualization_type == 'histogram' and x_axis:
        fig, ax = plt.subplots()
        df[x_axis].plot.hist(bins=10, ax=ax)
        ax.set_title('Histogram')
    elif visualization_type == 'area_chart' and x_axis and y_axis:
        fig, ax = plt.subplots()
        df.plot.area(x=x_axis, y=y_axis, ax=ax)
        ax.set_title('Area Chart')

    # Convert the plot to a base64 string for embedding in HTML
    img = BytesIO()
    fig.savefig(img, format='png')
    plt.close(fig)
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    return f'<img src="data:image/png;base64,{plot_url}" alt="{visualization_type}" />'
    
# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)