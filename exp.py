import os
import re
import matplotlib.pyplot as plt
import numpy as np


def parse_results(file_path):
    """
    Parse the statistics from a result file.

    Parameters:
        file_path (str): The path to the result file to parse.

    Returns:
        tuple: A tuple containing:
            - num_streams (int): The number of streams.
            - data_rate (float): The data rate in MB/sec.
            - packet_rate (float): The packet rate in packets/sec.
        None: If parsing fails due to missing or malformed data.
    """
    with open(file_path, 'r') as file:
        content = file.read()

    try:
        num_streams = int(re.search(r'Number of Streams: (\d+)', content).group(1))
        total_data_received = float(re.search(r'Total Data Received: [\d,]+ bytes \(([\d\.]+) MB\)', content).group(1))
        data_rate = float(re.search(r'Data Rate: ([\d\.]+) MB/sec', content).group(1))
        packet_rate = float(re.search(r'Packet Rate: ([\d\.]+) packets/sec', content).group(1))
    except AttributeError as e:
        print(f"Error parsing file {file_path}: {e}")
        return None

    return num_streams, data_rate, packet_rate


def collect_data(directory):
    """
    Collect data from all relevant result files in the specified directory.

    Parameters:
        directory (str): The directory containing result files.

    Returns:
        dict: A dictionary where keys are the number of streams, and values are dictionaries
              containing lists of 'data_rate' and 'packet_rate'.
    """
    data = {}
    pattern = re.compile(r'^\d+_streams_\d+\.\d+MB_\d+\.txt$')

    for file_name in os.listdir(directory):
        if pattern.match(file_name):  # Only process files matching the pattern
            file_path = os.path.join(directory, file_name)
            result = parse_results(file_path)
            if result:  # Only add valid results
                num_streams, data_rate, packet_rate = result
                if num_streams not in data:
                    data[num_streams] = {'data_rate': [], 'packet_rate': []}
                data[num_streams]['data_rate'].append(data_rate)
                data[num_streams]['packet_rate'].append(packet_rate)

    return data


def plot_whisker_chart(data, metric_key, metric_name, file_name):
    """
    Plot a whisker chart (box plot) comparing the selected metric (data rate or packet rate) by number of streams.

    Parameters:
        data (dict): The collected data for each number of streams.
        metric_key (str): The key for the metric to plot ('data_rate' or 'packet_rate').
        metric_name (str): The name of the metric for labeling purposes.
        file_name (str): The file name to save the generated plot.
    """
    # Prepare data for plotting
    stream_counts = list(range(1, 11))  # Ensure ticks for 1 to 10
    metric_data = [data.get(count, {}).get(metric_key, []) for count in stream_counts]

    # Plotting the whisker chart
    plt.figure(figsize=(10, 6))
    plt.boxplot(metric_data, labels=stream_counts)
    plt.xlabel('Number of Streams')
    plt.ylabel(metric_name)
    plt.title(f'{metric_name} vs. Number of Streams (Whisker Plot)')
    plt.grid(True)
    plt.xticks(ticks=stream_counts)

    # Save the chart to a file
    plt.savefig(file_name)
    plt.show()


def plot_median_and_average_line_chart(data, metric_key, metric_name, file_name):
    """
    Plot a line chart for both the median and average of the selected metric by number of streams.

    Parameters:
        data (dict): The collected data for each number of streams.
        metric_key (str): The key for the metric to plot ('data_rate' or 'packet_rate').
        metric_name (str): The name of the metric for labeling purposes.
        file_name (str): The file name to save the generated plot.
    """
    stream_counts = list(range(1, 11))  # Ensure ticks for 1 to 10
    median_values = [np.median(data.get(count, {}).get(metric_key, [0])) for count in stream_counts]
    average_values = [np.mean(data.get(count, {}).get(metric_key, [0])) for count in stream_counts]

    # Plotting the line chart with both median and average
    plt.figure(figsize=(10, 6))
    plt.plot(stream_counts, median_values, marker='o', color='blue', label='Median')
    plt.plot(stream_counts, average_values, marker='x', color='green', linestyle='--', label='Average')
    plt.xlabel('Number of Streams')
    plt.ylabel(metric_name)
    plt.title(f'Median and Average {metric_name} vs. Number of Streams')
    plt.legend()
    plt.grid(True)
    plt.xticks(ticks=stream_counts)

    # Save the chart to a file
    plt.savefig(file_name)
    plt.show()


if __name__ == "__main__":
    # Specify the directory where the result files are stored
    results_directory = 'out'

    # Collect data from the result files
    data = collect_data(results_directory)

    # Plot whisker charts and save them
    plot_whisker_chart(data, metric_key='data_rate', metric_name='Data Rate (MB/sec)', file_name='out/data_rate_whisker_plot.png')
    plot_whisker_chart(data, metric_key='packet_rate', metric_name='Packet Rate (packets/sec)', file_name='out/packet_rate_whisker_plot.png')

    # Plot median and average line charts and save them
    plot_median_and_average_line_chart(data, metric_key='data_rate', metric_name='Data Rate (MB/sec)', file_name='out/data_rate_median_average_line_plot.png')
    plot_median_and_average_line_chart(data, metric_key='packet_rate', metric_name='Packet Rate (packets/sec)', file_name='out/packet_rate_median_average_line_plot.png')
