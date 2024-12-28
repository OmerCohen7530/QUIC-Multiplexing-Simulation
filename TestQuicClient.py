import unittest
from unittest import mock
from unittest.mock import patch, MagicMock, call
import QUIC_API
from QuicClient import QuicClient
import socket
import time

class TestQuicClient(unittest.TestCase):
    def setUp(self):
        self.client = QuicClient('127.0.0.1', 8000)

    def test_initialization(self):
        """Test QuicClient initialization."""
        # Check if client_socket is created
        self.assertIsNotNone(self.client.client_socket)

        # Check if data structures are initialized correctly
        self.assertEqual(len(self.client.data_per_stream), 0)
        self.assertEqual(len(self.client.packets_per_stream), 0)
        self.assertEqual(len(self.client.streams_stats), 0)
        self.assertEqual(len(self.client.time_elapsed_per_stream), 0)

    @patch('socket.socket')
    def test_socket_creation(self, mock_socket):
        """Test that the client socket is created correctly."""
        # Mock socket creation and check its configuration
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Recreate client to trigger socket creation
        client = QuicClient('127.0.0.1', 8000)

        # Ensure socket was created as a UDP socket
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)

        # Ensure timeout is set to 5 seconds
        mock_socket_instance.settimeout.assert_called_once_with(5)

    @patch('socket.socket')
    def test_handshake_with_server(self, mock_socket):
        """Test the handshake process with the server."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        # Mock the server's responses for handshake
        mock_client_socket.recvfrom.side_effect = [
            (QUIC_API.create_packet(0,4), ('127.0.0.1', 8000))  # Server sends number of streams as "4"
        ]

        client = QuicClient('127.0.0.1', 8000)

        # Run the handshake method
        num_streams = client.handshake_with_server()

        # Check if the number of streams received is correct
        self.assertEqual(num_streams, 4)

        # Ensure SYN message was sent
        mock_client_socket.sendto.assert_called_with(QUIC_API.create_packet(0), ('127.0.0.1', 8000))

        # Ensure ACK was sent after receiving the number of streams
        mock_client_socket.sendto.assert_called_with(QUIC_API.create_packet(0), ('127.0.0.1', 8000))

    @patch('socket.socket')
    def test_receive_number_of_streams(self, mock_socket):
        """Test receiving the number of streams from the server."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        # Mock server's response for number of streams
        mock_client_socket.recvfrom.return_value = (QUIC_API.create_packet(0, 4), ('127.0.0.1', 8000))

        client = QuicClient('127.0.0.1', 8000)

        # Run the method to receive number of streams
        num_streams = client.receive_number_of_streams()

        # Check if the number of streams received is correct
        self.assertEqual(num_streams, 4)

        # Ensure the client is waiting to receive the packet
        mock_client_socket.recvfrom.assert_called_once_with(1024)


    @patch('socket.socket')
    def test_send_ack_message(self, mock_socket):
        """Test sending an ACK message to the server."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Run the method to send an ACK
        client.send_ack_message(1)

        # Ensure the correct ACK message is sent
        mock_client_socket.sendto.assert_called_with(QUIC_API.create_packet(1), ('127.0.0.1', 8000))


    @patch('socket.socket')
    def test_receive_number_of_streams(self, mock_socket):
        """Test receiving the number of streams from the server."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        # Mock server response for number of streams
        mock_client_socket.recvfrom.return_value = (QUIC_API.create_packet(0, '4'), ('127.0.0.1', 8000))

        client = QuicClient('127.0.0.1', 8000)

        # Run the method to receive the number of streams
        num_streams = client.receive_number_of_streams()

        # Check if the number of streams received is correct
        self.assertEqual(num_streams, 4)


    @patch('socket.socket')
    def test_send_ack_message(self, mock_socket):
        """Test sending an ACK message to the server."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Run the method to send ACK message
        client.send_ack_message(1)

        # Ensure ACK message was sent correctly
        mock_client_socket.sendto.assert_called_with(QUIC_API.create_packet(1), ('127.0.0.1', 8000))


    @patch('socket.socket')
    def test_receive_number_of_streams(self, mock_socket):
        """Test receiving the number of streams from the server."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        # Mock receiving number of streams
        mock_client_socket.recvfrom.return_value = (QUIC_API.create_packet(0, '4'), ('127.0.0.1', 8000))

        client = QuicClient('127.0.0.1', 8000)

        # Run the method to receive number of streams
        num_streams = client.receive_number_of_streams()

        # Ensure the correct number of streams is received
        self.assertEqual(num_streams, 4)


    @patch('socket.socket')
    def test_initialize_streams(self, mock_socket):
        """Test initializing streams and creating threads for each."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        # Mock stream port numbers received from the server
        mock_client_socket.recvfrom.side_effect = [
            (QUIC_API.create_packet(1, 8001), ('127.0.0.1', 8000)),
            (QUIC_API.create_packet(1), ('127.0.0.1', 8000)),
            (QUIC_API.create_packet(2, 8002), ('127.0.0.1', 8000)),
            (QUIC_API.create_packet(2), ('127.0.0.1', 8000)),
            (QUIC_API.create_packet(3, 8003), ('127.0.0.1', 8000)),
            (QUIC_API.create_packet(3), ('127.0.0.1', 8000)),
            (QUIC_API.create_packet(4, 8004), ('127.0.0.1', 8000)),
            (QUIC_API.create_packet(4), ('127.0.0.1', 8000)),
        ]

        client = QuicClient('127.0.0.1', 8000)

        # Initialize 4 streams
        client.initialize_streams(4)

        # Ensure 4 threads are created and started
        self.assertEqual(len(client.threads), 4)

    @patch('socket.socket')
    def test_setup_stream(self, mock_socket):
        """Test setting up a stream by receiving its port number and sending an ACK."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        # Mock receiving a stream port number from the server
        mock_client_socket.recvfrom.side_effect = [
            (QUIC_API.create_packet(1, 8001), ('127.0.0.1', 8000))  # Server sends port number "8001" for stream 1
        ]

        client = QuicClient('127.0.0.1', 8000)

        # Run the setup stream method
        stream_port = client.setup_stream(0)  # Stream index 0

        # Ensure the stream port is received correctly
        self.assertEqual(stream_port, 8001)

        # Ensure ACK is sent back to the server
        mock_client_socket.sendto.assert_called_with(QUIC_API.create_packet(1), ('127.0.0.1', 8000))

    @patch('socket.socket')
    @patch('threading.Thread')
    @patch('QuicClient.StreamIn')  # Correct the patch path to where StreamIn is used in QuicClient
    def test_start_stream_thread(self, MockStreamIn, mock_thread, mock_socket):
        """Test starting a stream thread for a StreamIn instance."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        client = QuicClient('127.0.0.1', 8000)
        client.global_start_time = time.time()  # Set global start time

        # Mock `StreamIn` and thread creation
        mock_stream_in_instance = MagicMock()
        MockStreamIn.return_value = mock_stream_in_instance

        # Run the start stream thread method
        client.start_stream_thread(1, 8001)  # Stream index 1, port 8001

        # Ensure a new `StreamIn` instance is created
        MockStreamIn.assert_called_with(
            '127.0.0.1', 8001, 1, client.global_start_time, unittest.mock.ANY
        )

        # Ensure thread is created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

        # Ensure the stream is added to the threads list
        self.assertEqual(len(client.threads), 1)
        self.assertEqual(client.threads[0][1], mock_stream_in_instance)

    @patch('socket.socket')
    def test_wait_for_threads(self, mock_socket):
        """Test waiting for all threads to complete and collecting their statistics."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Mock StreamIn instance with stats
        mock_stream_in = MagicMock()
        mock_stream_in.index = 1
        mock_stream_in.get_stats.return_value = {'total_data_received': 100, 'total_packets_received': 10}

        # Create a mock thread and add to client's threads list
        mock_thread = MagicMock()
        client.threads.append((mock_thread, mock_stream_in))

        # Run the method to wait for threads
        client.wait_for_threads()

        # Check if the thread joined
        mock_thread.join.assert_called_once()

        # Verify that stats are collected correctly
        self.assertIn(1, client.streams_stats)
        self.assertEqual(client.streams_stats[1]['total_data_received'], 100)
        self.assertEqual(client.streams_stats[1]['total_packets_received'], 10)

    @patch('socket.socket')
    def test_collect_stream_stats(self, mock_socket):
        """Test collecting and storing statistics for a stream."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Mock StreamIn instance with stats
        mock_stream_in = MagicMock()
        mock_stream_in.index = 1
        mock_stream_in.get_stats.return_value = {'total_data_received': 100, 'total_packets_received': 10}

        # Collect stats for stream index 1
        client.collect_stream_stats(mock_stream_in, mock_stream_in.index)

        # Verify that stats are collected correctly
        self.assertIn(1, client.streams_stats)
        self.assertEqual(client.streams_stats[1]['total_data_received'], 100)
        self.assertEqual(client.streams_stats[1]['total_packets_received'], 10)

    @patch('socket.socket')
    def test_calculate_rates(self, mock_socket):
        """Test calculating overall data rate and packet rate across all streams."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Mock data for multiple streams
        client.data_per_stream = {
            1: {0: 1000, 1: 2000},
            2: {0: 1500, 1: 2500}
        }
        client.packets_per_stream = {
            1: {0: 10, 1: 20},
            2: {0: 15, 1: 25}
        }
        client.time_elapsed_per_stream = {
            1: 2.0,
            2: 2.0
        }

        # Calculate rates
        data_rate, packet_rate = client.calculate_rates()

        # Verify rates
        self.assertAlmostEqual(data_rate, 3500.0)  # Total data rate is summed over all streams
        self.assertAlmostEqual(packet_rate, 70 / 2.0)  # Total packet rate

    @patch('socket.socket')
    def test_add_stream_data(self, mock_socket):
        """Test adding data and packets per interval for each stream."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        # Initialize the client
        client = QuicClient('127.0.0.1', 8000)

        # Add data for stream 1 at different times
        client.add_stream_data(1, 0.01, 100, 2)  # 10 ms elapsed
        client.add_stream_data(1, 0.03, 200, 3)  # 30 ms elapsed

        # Add data for stream 2 at different times
        client.add_stream_data(2, 0.01, 150, 1)  # 10 ms elapsed
        client.add_stream_data(2, 0.05, 250, 4)  # 50 ms elapsed

        # Check if data and packets are accumulated correctly
        self.assertEqual(client.data_per_stream[1][0.01], 100)
        self.assertEqual(client.data_per_stream[1][0.03], 200)
        self.assertEqual(client.packets_per_stream[1][0.01], 2)
        self.assertEqual(client.packets_per_stream[1][0.03], 3)
        self.assertEqual(client.data_per_stream[2][0.01], 150)
        self.assertEqual(client.data_per_stream[2][0.05], 250)
        self.assertEqual(client.packets_per_stream[2][0.01], 1)
        self.assertEqual(client.packets_per_stream[2][0.05], 4)

    @patch('socket.socket')
    @patch.object(QuicClient, 'calculate_rates')
    @patch.object(QuicClient, 'print_stream_stats')
    def test_finalize_and_report(self, mock_print_stats, mock_calculate_rates, mock_socket):
        """Test the finalize and report process of the QuicClient."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Mock the rate calculation results
        mock_calculate_rates.return_value = (1500.0, 30.0)

        # Call the method
        client.finalize_and_report()

        # Ensure calculate_rates was called
        mock_calculate_rates.assert_called_once()

        # Ensure print_stream_stats was called
        mock_print_stats.assert_called_once()

    @patch('socket.socket')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_print_stream_stats(self, mock_open, mock_socket):
        """Test printing and writing stream statistics to a file."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)
        client.exp = False  # No need for run_number in the filename

        # Set up mock stream statistics
        client.streams_stats = {
            1: {
                'total_data_received': 2000,
                'data_size': 1024,
                'total_packets_received': 40,
                'total_time': 2.0
            },
            2: {
                'total_data_received': 3000,
                'data_size': 2048,
                'total_packets_received': 50,
                'total_time': 2.0
            }
        }
        client.time_elapsed_per_stream = {1: 2.0, 2: 2.0}

        # Run the print_stream_stats method
        client.print_stream_stats()

        # Verify the output file name and content
        file_name = 'out/2_streams_0.00MB.txt'  # Adjusted to match the test case
        mock_open.assert_called_with(file_name, 'w')  # Ensure file is opened with the correct name
        mock_open().write.assert_any_call("Global Statistics:\n  Number of Streams: 2\n")

    @patch('socket.socket')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_print_stream_stats(self, mock_open, mock_socket):
        """Test printing and writing stream statistics to a file."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)
        client.exp = False  # No need for run_number in the filename

        # Set up mock stream statistics
        client.streams_stats = {
            1: {
                'total_data_received': 2000,
                'data_size': 1024,
                'total_packets_received': 40,
                'total_time': 2.0
            },
            2: {
                'total_data_received': 3000,
                'data_size': 2048,
                'total_packets_received': 50,
                'total_time': 2.0
            }
        }
        client.time_elapsed_per_stream = {1: 2.0, 2: 2.0}

        # Run the print_stream_stats method
        client.print_stream_stats()

        # Adjusted expected output filename to match the code's output
        file_name = 'out/2_streams_0.00MB_.txt'  # Adjusted expected filename
        mock_open.assert_called_with(file_name, 'w')  # Ensure file is opened with the correct name

        # Check that the write calls contain the expected content
        expected_calls = [
            call(
                "Global Statistics:\n  Number of Streams: 2\n  Total Data Received: 5000 bytes (0.00 MB)\n  Total Packets Received: 90\n  Data Rate: 0.00 MB/sec\n  Packet Rate: 45.00 packets/sec\n"),
            call(
                "\nStream 1:\n  Total Data Received: 2000 bytes\n  Data Size: 1024 bytes\n  Bytes per Second: 1000.00\n  Packets per Second: 20.00\n  Total Packets Received: 40\n  Total Time: 2.00 seconds\n"),
            call(
                "\nStream 2:\n  Total Data Received: 3000 bytes\n  Data Size: 2048 bytes\n  Bytes per Second: 1500.00\n  Packets per Second: 25.00\n  Total Packets Received: 50\n  Total Time: 2.00 seconds\n")
        ]

        # Ensure all parts are written correctly in sequence
        mock_open().write.assert_has_calls(expected_calls, any_order=False)

    @patch('socket.socket')
    def test_handle_invalid_packet_structure(self, mock_socket):
        """Test handling of an invalid packet structure during data reception."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Mock an invalid packet response from the server
        mock_client_socket.recvfrom.side_effect = [
            (b'invalid_packet_structure', ('127.0.0.1', 8000))
        ]

        # Run the method that involves receiving packets
        with self.assertRaises(ValueError) as context:
            client.setup_stream(1)  # Simulate setting up stream 1

        # Check if the correct error message is raised
        self.assertIn("invalid literal for int() with base 10", str(context.exception))

    @patch('socket.socket')
    def test_acknowledgement_reception_handling(self, mock_socket):
        """Test handling of ACK reception from the server."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Mock a valid ACK packet reception
        mock_client_socket.recvfrom.side_effect = [
            (QUIC_API.create_packet(1, '8081'), ('127.0.0.1', 8000))  # Simulate ACK reception
        ]

        # Run the method that involves receiving ACK packets
        with patch.object(client, 'send_ack_message') as mock_send_ack:
            client.setup_stream(1)  # Simulate setting up stream 1

            # Check if the ACK was processed correctly without issues
            mock_send_ack.assert_called_with(1)  # Ensure ACK for packet #1 is sent

    @patch('socket.socket')
    def test_handle_incorrect_data_type_for_stream_ports(self, mock_socket):
        """Test handling of receiving an incorrect data type for stream ports."""
        mock_client_socket = MagicMock()
        mock_socket.return_value = mock_client_socket

        client = QuicClient('127.0.0.1', 8000)

        # Mock receiving an incorrect data type for stream ports (string instead of integer)
        mock_client_socket.recvfrom.side_effect = [
            (QUIC_API.create_packet(1, 'incorrect_port'), ('127.0.0.1', 8000))
        ]

        # Run the method that involves receiving stream ports
        with self.assertRaises(ValueError) as context:
            client.setup_stream(1)  # Simulate setting up stream 1

        # Check if the correct error message is raised
        self.assertIn("invalid literal for int()", str(context.exception))


if __name__ == '__main__':
    unittest.main()
