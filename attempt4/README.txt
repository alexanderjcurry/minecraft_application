Can access website through tailscale via tailscale ip to system running minecraft server and port number of the coresponding minecraft server running on docker. Port number for intial website acces is 4242.


To start it from scratch do this:

Show chatgpt all my dependencies from the app.py file and tell it to provide me commands to download them all.

To start flask go to folder where app.py is stored: python3 app.py

To start webhook may have to install webhook local enviorment from stripe website then run this command: stripe listen --forward-to localhost:4242/webhook

https://stripe.com/docs/stripe-cli

Access website via 127.0.0.1:4242

Make sure these keys are in the app.py file:

pk_test_51OOrdBJxVhVlFzT6OiXm7CHTdha9KbmWYIBbH6rVE3lu0oE1niiL9ICECqEjDrxj91Jjf0hSJ930YMUSAwvUzUSJ00Q6Xb1t1f

sk_test_51OOrdBJxVhVlFzT6R5aUvfjWylPxQL9hStgb7wl3ilvzcozq43IhaDgQ9AQaV2nqJX1Dr8wTIz8KOJmWj4EyILJl00U6T4T3iu

whsec_a11df43f0859ebda9e32248536b3562e547760102bd8a41636fee195401c31cd


CHANGES MADE:

-Stripe now funcitons and takes payments