import socket
import threading
import time
from collections import defaultdict
from StreamIn import StreamIn
import QUIC_API
from functools import partial  # Import partial for function binding

class QuicClient:
    """
    QUIC client that communicates with a QUIC server, handles multiple streams,
    and computes various statistics like data rate and packet rate.

    Attributes:
        server_host (str): The server's IP address.
        server_port (int): The server's port number.
        exp (bool): Flag indicating if this is an experiment run.
        client_socket (socket.socket): The UDP socket for the client.
        threads (list): List of threads for handling each stream.
        global_start_time (float): Start time for the entire communication session.
        data_per_stream (defaultdict): Data received per stream and interval.
        packets_per_stream (defaultdict): Packets received per stream and interval.
        streams_stats (dict): Statistics for each stream.
        time_elapsed_per_stream (dict): Elapsed time for each stream.
    """

    def __init__(self, server_host, server_port, exp=False):
        """
        Initializes the QUIC client with the server's address and connection parameters.

        Parameters:
            server_host (str): The server's IP address.
            server_port (int): The server's port number.
            exp (bool): Indicates if the client is running in experiment mode.
        """
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = self.create_socket()
        self.threads = []
        self.global_start_time = None
        self.exp = exp
        self.data_per_stream = defaultdict(lambda: defaultdict(int))
        self.packets_per_stream = defaultdict(lambda: defaultdict(int))
        self.streams_stats = {}
        self.time_elapsed_per_stream = {}

    def create_socket(self):
        """
        Creates and configures a UDP socket for the client.

        Returns:
            socket.socket: A configured UDP socket.
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(5)  # Set a timeout for receiving
        return client_socket

    def handshake_with_server(self):
        """
        Handles the handshake process with the server.

        This method sends a SYN message to the server and waits to receive the number of streams.

        Returns:
            int: The number of streams specified by the server.
        """
        while True:
            try:
                self.send_syn_message()
                num_streams = self.receive_number_of_streams()
                self.send_ack_message(0)  # Acknowledge receiving the number of streams
                return num_streams
            except socket.timeout:
                print("Timeout while waiting for a message from server. Trying again.")

    def send_syn_message(self):
        """
        Sends a SYN message to the server to initiate the connection.
        """
        syn_message = QUIC_API.create_packet(0, 'Syn')
        self.client_socket.sendto(syn_message, (self.server_host, self.server_port))
        print(f"Sent SYN to {self.server_host}:{str(self.server_port)}")

    def receive_number_of_streams(self):
        """
        Receives the number of streams from the server.

        Returns:
            int: The number of streams to be handled.
        """
        packet, _ = self.client_socket.recvfrom(1024)
        packet_num, num_streams = QUIC_API.parse_packet(packet)
        num_streams = int(num_streams)  # Convert the number of streams to an integer
        print(f"Received number of streams: {num_streams}")
        return num_streams

    def send_ack_message(self, packet_num):
        """
        Sends an ACK message to the server for the received packet.

        Parameters:
            packet_num (int): The number of the packet being acknowledged.
        """
        ack_message = QUIC_API.create_packet(packet_num)
        self.client_socket.sendto(ack_message, (self.server_host, self.server_port))
        print(f"Sent ACK for packet #{packet_num}")

    def start(self):
        """
        Starts the client by initiating the handshake, creating streams,
        waiting for threads to finish, and reporting the results.
        """
        try:
            num_streams = self.handshake_with_server()
            self.global_start_time = time.time()
            self.initialize_streams(num_streams)
            self.wait_for_threads()
            self.finalize_and_report()
        except Exception as e:
            print(f"Error in QuicClient: {e}")

    def initialize_streams(self, num_streams):
        """
        Initializes streams and creates threads for each stream.

        Parameters:
            num_streams (int): The number of streams to be initialized.
        """
        for i in range(num_streams):
            stream_port = self.setup_stream(i)
            self.start_stream_thread(i + 1, stream_port)

    def setup_stream(self, stream_index):
        """
        Sets up each stream by receiving its port number from the server and sending an ACK.

        Parameters:
            stream_index (int): Index of the stream being set up.

        Returns:
            int: The port number for the stream.
        """
        packet, _ = self.client_socket.recvfrom(1024)
        packet_num, stream_port = QUIC_API.parse_packet(packet)
        stream_port = int(stream_port)  # Convert the stream port to an integer
        print(f"Received stream {stream_index + 1} port: {stream_port}")
        self.send_ack_message(packet_num)
        return stream_port

    def start_stream_thread(self, index, stream_port):
        """
        Creates and starts a thread for each StreamIn instance.

        Parameters:
            index (int): Index of the stream.
            stream_port (int): The port number for the stream.
        """
        # Use partial to bind index to add_stream_data method
        stream_data_callback = partial(self.add_stream_data, index)

        # Initialize StreamIn with the bound callback
        stream_in = StreamIn(
            self.server_host,
            stream_port,
            index,
            self.global_start_time,
            stream_data_callback  # Pass the callback with the bound index
        )

        thread = threading.Thread(target=stream_in.start)
        thread.start()
        self.threads.append((thread, stream_in))

    def wait_for_threads(self):
        """
        Waits for all stream threads to complete and collects their statistics.
        """
        for thread, stream_in in self.threads:
            thread.join()
            self.collect_stream_stats(stream_in, stream_in.index)

    def collect_stream_stats(self, stream_in, index):
        """
        Collects and stores the statistics for a stream.

        Parameters:
            stream_in (StreamIn): The StreamIn instance for the stream.
            index (int): Index of the stream.
        """
        self.streams_stats[index] = stream_in.get_stats()

    def finalize_and_report(self):
        """
        Finalizes the experiment and reports the results.
        """
        data_rate, packet_rate = self.calculate_rates()
        print(f"\nData Rate (Bytes/Second): {data_rate:.2f}")
        print(f"Packet Rate (Packets/Second): {packet_rate:.2f}")
        self.print_stream_stats()

    def calculate_rates(self):
        """
        Calculates the overall data rate and packet rate across all streams.

        Returns:
            tuple: Overall data rate in bytes per second and packet rate in packets per second.
        """
        total_data = sum(sum(stream_data.values()) for stream_data in self.data_per_stream.values())
        total_packets = sum(sum(stream_packets.values()) for stream_packets in self.packets_per_stream.values())
        total_time = max(self.time_elapsed_per_stream.values())  # Total time for longest stream
        data_rate = total_data / total_time if total_time > 0 else 0
        packet_rate = total_packets / total_time if total_time > 0 else 0
        return data_rate, packet_rate

    def add_stream_data(self, stream_index, time_elapsed, data_received, packets_received):
        """
        Accumulates data and packets per interval for each stream in a thread-safe manner.

        Parameters:
            stream_index (int): Index of the stream.
            time_elapsed (float): Time elapsed since the start of the stream.
            data_received (int): Amount of data received.
            packets_received (int): Number of packets received.
        """

        self.data_per_stream[stream_index][time_elapsed] += data_received
        self.packets_per_stream[stream_index][time_elapsed] += packets_received
        self.time_elapsed_per_stream[stream_index] = time_elapsed

    def print_stream_stats(self):
        """
        Prints global statistics across all streams and writes them to a dynamically named file.
        """
        if self.exp:
            global run_number  # Access the global run number

        total_data_received = sum(stats['total_data_received'] for stats in self.streams_stats.values())
        total_packets_received = sum(stats['total_packets_received'] for stats in self.streams_stats.values())
        num_streams = len(self.streams_stats)
        total_size_mb = total_data_received / (1024 * 1024)
        total_time = max(self.time_elapsed_per_stream.values())
        data_rate_mb_sec = total_size_mb / total_time if total_time > 0 else 0
        packet_rate_sec = total_packets_received / total_time if total_time > 0 else 0

        file_name = f'out/{num_streams}_streams_{total_size_mb:.2f}MB_{run_number if self.exp else ""}.txt'

        with open(file_name, 'w') as file:
            global_output = (
                f"Global Statistics:\n"
                f"  Number of Streams: {num_streams}\n"
                f"  Total Data Received: {total_data_received} bytes ({total_size_mb:.2f} MB)\n"
                f"  Total Packets Received: {total_packets_received}\n"
                f"  Data Rate: {data_rate_mb_sec:.2f} MB/sec\n"
                f"  Packet Rate: {packet_rate_sec:.2f} packets/sec\n"
            )
            print(global_output)
            file.write(global_output)

            for index, stats in self.streams_stats.items():
                stream_total_time = self.time_elapsed_per_stream[index]
                output = (
                    f"\nStream {index}:\n"
                    f"  Total Data Received: {stats['total_data_received']} bytes\n"
                    f"  Data Size: {stats['data_size']} bytes\n"
                    f"  Bytes per Second: {stats['total_data_received'] / stream_total_time:.2f}\n"
                    f"  Packets per Second: {stats['total_packets_received'] / stream_total_time:.2f}\n"
                    f"  Total Packets Received: {stats['total_packets_received']}\n"
                    f"  Total Time: {stream_total_time:.2f} seconds\n"
                )
                print(output)
                file.write(output)

if __name__ == "__main__":
    # for i in range(2, 4):
    #     run_number = 0
    #     for j in range(50):
    #         run_number += 1
    #         client = QuicClient('127.0.0.1', 8000, exp=True)
    #         client.start()
    client = QuicClient('127.0.0.1', 8000, exp=True)
    client.start()
