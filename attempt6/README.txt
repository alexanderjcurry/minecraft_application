Changes made from previous:

Added admin page with lots of javascripts to start and stop the server.
It also shows the subscription plan chosen along witht he server name, port and status of it runnning or not.

Notes:
Starting is instant while stop takes 10 seconds at times. Maybe add a loading wheel would be good.


TO START:

stripe listen --forward-to localhost:4242/webhook

python3 app.py