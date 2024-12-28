import random
import socket
import threading
import os
import QUIC_API
from StreamOut import StreamOut

class QuicServer:
    """
    QUIC server that listens for incoming client connections, handles multiple data streams,
    and coordinates data transfer using threads.

    Attributes:
        host (str): The server's IP address.
        port (int): The server's port number.
        streams (int): Number of streams to handle.
        ack_timeout (int): Timeout in seconds for waiting for client acknowledgments.
        is_test (bool): Flag indicating if this is a test run.
        uniform_size (int): Uniform size for each stream file during testing.
        server_socket (socket.socket): The UDP socket for the server.
        sizes (list): List of sizes for each stream file.
        threads (list): List of threads handling each stream.
        client_address (tuple): Address of the connected client.
    """

    def __init__(self, host, port, streams, total_size=0.1, ack_timeout=5, is_test=False, uniform_size=None):
        """
        Initializes the QUIC server with the specified host, port, and other parameters.

        Parameters:
            host (str): The server's IP address.
            port (int): The server's port number.
            streams (int): The number of streams to handle.
            total_size (float): The total size of data to be distributed across streams (in MB).
            ack_timeout (int): Timeout in seconds for client acknowledgment.
            is_test (bool): Indicates if the server is running in test mode.
            uniform_size (int): Uniform size for each stream file during testing.
        """
        self.host = host
        self.port = port
        self.streams = streams
        self.ack_timeout = ack_timeout
        self.is_test = is_test
        self.uniform_size = uniform_size
        self.server_socket = self.create_server_socket()
        self.sizes = []
        self.threads = []
        self.client_address = None  # Initialize client_address as None

        # Ensure the output directory exists
        os.makedirs('out', exist_ok=True)
        print("QuicServer starts")
        self.create_stream_data_files(total_size)

    def create_server_socket(self):
        """
        Initializes and configures the server's UDP socket.

        Returns:
            socket.socket: A configured UDP socket for the server.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        print(f"Server listening on {self.host}:{self.port}")
        return server_socket

    def create_stream_data_files(self, total_size):
        """
        Creates data files for each stream based on the total size specified.

        Parameters:
            total_size (float): Total size of data to be divided among the streams (in MB).
        """
        for i in range(self.streams):
            size = self.uniform_size if self.is_test and self.uniform_size else random.randint(1000, 2001)
            self.sizes.append(size)
            data = QUIC_API.create_data(int(1024 * 1024 * (total_size / self.streams)))
            QUIC_API.create_file(data, i + 1)
            print(f"File {i + 1} created with size {int(1024 * 1024 * (total_size / self.streams))} bytes")

    def wait_for_client_syn(self):
        """
        Waits for a SYN message from the client to start the connection.
        """
        packet, self.client_address = self.server_socket.recvfrom(1024)  # Assign client_address
        packet_num, data = QUIC_API.parse_packet(packet)
        if data == "Syn":
            print(f"The client {self.client_address} sent a SYN message")
        else:
            raise ValueError("Invalid SYN message received")

    def send_number_of_streams(self):
        """
        Sends the number of streams to the client.
        """
        packet = QUIC_API.create_packet(0, str(self.streams))
        self.server_socket.sendto(packet, self.client_address)
        print(f"Sent number of streams: {self.streams}")

    def wait_for_ack(self, expected_packet_num):
        """
        Waits for an acknowledgment (ACK) from the client.

        Parameters:
            expected_packet_num (int): The packet number for which an ACK is expected.

        Returns:
            bool: True if the expected ACK is received, False otherwise.
        """
        try:
            ack_message, _ = self.server_socket.recvfrom(1024)
            packet_number, _ = QUIC_API.parse_packet(ack_message)
            if packet_number == expected_packet_num:
                print(f"Received ACK for packet #{expected_packet_num}")
                return True
            else:
                print(f"Expected ACK, but received: {packet_number}")
        except socket.timeout:
            print(f"Timeout waiting for ACK for packet #{expected_packet_num}.")
        return False

    def start_stream_threads(self):
        """
        Starts threads for handling each stream.
        """
        for i in range(self.streams):
            stream_port = self.port + i + 1
            self.start_stream_thread(i, stream_port)

    def start_stream_thread(self, stream_index, stream_port):
        """
        Starts a thread to handle a single stream.

        Parameters:
            stream_index (int): Index of the stream to handle.
            stream_port (int): Port number assigned to the stream.
        """
        stream = StreamOut(self.host, stream_port, self.sizes[stream_index], stream_index + 1)
        thread = threading.Thread(target=stream.start)
        thread.start()
        self.threads.append(thread)

        # Send the port number to the client
        self.send_stream_port_to_client(stream_index, stream_port)
        self.wait_for_ack(stream_index + 1)

    def send_stream_port_to_client(self, stream_index, stream_port):
        """
        Sends the port number for a stream to the client.

        Parameters:
            stream_index (int): Index of the stream.
            stream_port (int): Port number assigned to the stream.
        """
        packet = QUIC_API.create_packet(stream_index + 1, str(stream_port))
        self.server_socket.sendto(packet, self.client_address)
        print(f"Sent stream {stream_index + 1} port: {stream_port}")

    def wait_for_all_threads(self):
        """
        Waits for all stream threads to complete their tasks.
        """
        for thread in self.threads:
            thread.join()
        print("All streams have completed.")

    def start(self):
        """
        Starts the server and handles communication with the client.
        """
        try:
            self.wait_for_client_syn()  # No need to assign return value; it's now a data field
            self.send_number_of_streams()
            self.server_socket.settimeout(self.ack_timeout)
            if self.wait_for_ack(0):
                self.start_stream_threads()
                self.wait_for_all_threads()
        except Exception as e:
            print(f"Error in QuicServer: {e}")

if __name__ == "__main__":
    # for i in range(1, 9,7):
    #     for j in range(50):
    #         server = QuicServer('127.0.0.1', 8000, i, total_size=20, ack_timeout=5, is_test=True, uniform_size=2000)
    #         server.start()
    server = QuicServer('127.0.0.1', 8000, 4, total_size=20, ack_timeout=5, is_test=True, uniform_size=2000)
    server.start()
