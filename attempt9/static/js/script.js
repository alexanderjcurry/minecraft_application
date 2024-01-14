document.addEventListener('DOMContentLoaded', (event) => {
    var socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('connect', function() {
        console.log('Websocket connected!');
    });

    socket.on('docker_output', function(data) {
        var terminal = document.getElementById('dockerTerminal');
        terminal.value += data.output;  // Append the new output
        terminal.scrollTop = terminal.scrollHeight;  // Auto-scroll to the bottom
    });

    document.getElementById('sendButton').addEventListener('click', function() {
        var command = document.getElementById('commandInput').value;
        socket.emit('send_command', {command: command});
        document.getElementById('commandInput').value = '';  // Clear the input field
    });
});
