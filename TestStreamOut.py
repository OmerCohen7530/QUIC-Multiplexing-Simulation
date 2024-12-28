import unittest
from unittest.mock import patch, mock_open, MagicMock
import socket  # Import socket module
from StreamOut import StreamOut
import QUIC_API


def create_packet(packet_num, data=''):
    """Utility function to create a packet for testing."""
    return QUIC_API.create_packet(packet_num, data)

class TestStreamOut(unittest.TestCase):
    def setUp(self):
        # Initialize StreamOut instance with mocked parameters
        self.stream_out = StreamOut('127.0.0.1', 9000, 2048, 1)
        self.stream_out.socket.close()

    def tearDown(self):
        # Ensure the socket is closed after each test
        if self.stream_out.socket and not self.stream_out.socket._closed:
            self.stream_out.socket.close()
        if self.stream_out.log_file and not self.stream_out.log_file.closed:
            self.stream_out.log_file.close()

    @patch('socket.socket')  # Mock the socket creation
    def test_wait_for_client_syn(self, mock_socket):
        # Create a mock socket instance
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket

        # Replace the socket in the StreamOut instance with our mock socket
        self.stream_out.socket = mock_stream_socket

        # Use side_effect to simulate multiple recvfrom calls
        mock_stream_socket.recvfrom.side_effect = [
            (b'00000000 Syn', ('127.0.0.1', 5000)),  # Simulate receiving a SYN message from the client
        ]

        # Call the method to test
        self.stream_out.wait_for_client_syn()

        # Assertions to check if the method correctly set the client address
        self.assertEqual(self.stream_out.client_address, ('127.0.0.1', 5000))
        self.assertEqual(self.stream_out.packet_num, 0)  # Initial packet number should be 0

        # Ensure recvfrom was called once
        mock_stream_socket.recvfrom.assert_called_once()

    @patch('socket.socket')
    def test_send_data_flow(self, mock_socket):
        """Test sending data packets and waiting for ACKs."""
        # Create a mock socket instance
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket

        # Replace the socket in the StreamOut instance with our mock socket
        self.stream_out.socket = mock_stream_socket

        # Set client address for sending and receiving packets
        self.stream_out.client_address = ('127.0.0.1', 5000)

        # Simulate receiving an ACK and setting a sequence of recvfrom responses
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(0, 'ACK'), ('127.0.0.1', 5000)),  # Simulate ACK for packet 0
            socket.timeout(),  # Simulate a timeout (no ACK received)
            (create_packet(0, 'ACK'), ('127.0.0.1', 5000)),  # Simulate ACK for packet 0 after a retry
            (create_packet(1, 'ACK'), ('127.0.0.1', 5000)),  # Simulate ACK for packet 1 after another retry
        ]

        # Simulate sending data packets and waiting for ACKs
        print("Sending packet 1...")
        self.stream_out.send_packet('test data 1')
        print("Waiting for ACK for packet 1...")
        self.stream_out.wait_for_ack_with_retry('test data 1')
        print("ACK received for packet 1.")

        print("Sending packet 2...")
        self.stream_out.send_packet('test data 2')
        print("Waiting for ACK for packet 2...")
        self.stream_out.wait_for_ack_with_retry('test data 2')
        print("ACK received for packet 2.")

        # Verify that the sendto method is called correctly
        self.assertEqual(mock_stream_socket.sendto.call_count, 3)  # 2 original packets + retry
        self.assertEqual(mock_stream_socket.recvfrom.call_count, 4)

    @patch('socket.socket')
    def test_multiple_timeouts_then_success(self, mock_socket):
        """Test that the client retries on multiple timeouts and eventually succeeds."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_out.socket = mock_stream_socket
        self.stream_out.client_address = ('127.0.0.1', 5000)

        # Simulate multiple timeouts and a final successful ACK
        mock_stream_socket.recvfrom.side_effect = [
            socket.timeout(),  # Timeout
            socket.timeout(),  # Timeout
            (create_packet(0, 'ACK'), ('127.0.0.1', 5000)),  # Successful ACK for packet 0
        ]

        self.stream_out.send_packet('test data')
        self.stream_out.wait_for_ack_with_retry('test data')

        self.assertEqual(mock_stream_socket.sendto.call_count, 3)  # Two retries + original
        self.assertEqual(mock_stream_socket.recvfrom.call_count, 3)  # Two timeouts + successful recv

    @patch('socket.socket')
    def test_send_data_without_syn(self, mock_socket):
        """Test that an error is raised if send_data_from_file is called without client SYN."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_out.socket = mock_stream_socket

        with self.assertRaises(Exception) as context:
            self.stream_out.send_data_from_file()

        self.assertIn('Client not connected', str(context.exception))  # Adjust based on actual exception message

    @patch('socket.socket')
    def test_proper_closure_after_sending(self, mock_socket):
        """Test that sockets and log files are properly closed after data transmission."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_out.socket = mock_stream_socket
        self.stream_out.client_address = ('127.0.0.1', 5000)

        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(0, 'ACK'), ('127.0.0.1', 5000)),  # Successful ACK for packet 0
        ]

        self.stream_out.send_packet('test data')
        self.stream_out.wait_for_ack_with_retry('test data')

        self.stream_out.close_resources()  # Ensure resources are closed
        self.assertTrue(self.stream_out.log_file.closed)

    @patch('socket.socket')
    def test_incorrect_ack_handling(self, mock_socket):
        """Test handling of incorrect ACKs."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_out.socket = mock_stream_socket
        self.stream_out.client_address = ('127.0.0.1', 5000)

        # Simulate receiving incorrect ACKs
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(1, 'ACK'), ('127.0.0.1', 5000)),  # Incorrect ACK
            socket.timeout(),  # Timeout
            (create_packet(0, 'ACK'), ('127.0.0.1', 5000)),  # Correct ACK for packet 0
        ]

        self.stream_out.send_packet('test data')
        self.stream_out.wait_for_ack_with_retry('test data')

        self.assertEqual(mock_stream_socket.recvfrom.call_count, 3)  # Incorrect ACK + timeout + correct ACK

    @patch('socket.socket')
    def test_empty_data_packet(self, mock_socket):
        """Test handling of sending an empty data packet."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_out.socket = mock_stream_socket
        self.stream_out.client_address = ('127.0.0.1', 5000)

        self.stream_out.send_packet('')  # Send an empty data packet
        mock_stream_socket.sendto.assert_called_once()  # Ensure sendto was still called

    @patch('socket.socket')
    @patch('builtins.open', new_callable=mock_open, read_data='data1\n')
    def test_receive_eof_signal(self, mock_file, mock_socket):
        """Test that EOF is handled properly when the end of file is reached."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_out.socket = mock_stream_socket
        self.stream_out.client_address = ('127.0.0.1', 5000)

        # Simulate ACK response to each packet
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(0, 'ACK'), ('127.0.0.1', 5000)),  # Simulate ACK for packet 0
        ]

        # Simulate end of file by returning an empty string on the next read
        mock_file().read.side_effect = ['data1\n', '']

        # Mock the log method to prevent actual file I/O during logging
        with patch.object(self.stream_out, 'log', wraps=self.stream_out.log) as mock_log, \
                patch.object(self.stream_out,
                             'close_resources') as mock_close_resources:

            # Run the method that processes sending data
            self.stream_out.send_data_from_file()  # Should reach EOF after reading the mock file content

            # Call send_eof before closing the resources
            self.stream_out.send_eof()

            # Ensure "Completed sending data. Sent EOF." is logged
            mock_log.assert_any_call(f"Completed sending data. Sent EOF.")

    @patch('socket.socket')
    def test_proper_logging(self, mock_socket):
        """Test that events are properly logged."""
        mock_stream_socket = MagicMock()
        mock_socket.return_value = mock_stream_socket
        self.stream_out.socket = mock_stream_socket
        self.stream_out.client_address = ('127.0.0.1', 5000)

        # Simulate a series of events
        mock_stream_socket.recvfrom.side_effect = [
            (create_packet(0, 'ACK'), ('127.0.0.1', 5000)),  # Simulate ACK
        ]

        # Make sure log file is opened correctly
        assert not self.stream_out.log_file.closed, "Log file should be open at the start of the test."

        # Mock the log method to monitor its calls
        with patch.object(self.stream_out, 'log', wraps=self.stream_out.log) as mock_log:
            # Perform actions that should be logged
            self.stream_out.send_packet('test data')
            self.stream_out.wait_for_ack_with_retry('test data')

            # Force flushing to ensure log is written immediately
            self.stream_out.log_file.flush()

            # Print log calls to debug if they were made
            print("Log method calls:", mock_log.call_args_list)  # Debug print to check log calls

            # Read log file content
            with open(self.stream_out.log_file.name, 'r') as f:
                log_content = f.read()
                print(f"Log content: {log_content}")  # Debug print to check the log content

            # Assertions to check for the expected log messages
            self.assertIn('Sent packet', log_content)  # Ensure 'Sent packet' is in log
            self.assertIn('Received ACK for packet', log_content)  # Ensure 'Received ACK for packet' is in log


if __name__ == '__main__':
    unittest.main()
