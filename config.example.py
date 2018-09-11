# Must be a mysql database!
database_uri = 'sqlite:///pushjet_api.db'

# Are we debugging the server?
# Do not turn this on when in production!
debug = False

# Google Cloud Messaging configuration (required for android!)
google_api_key = ''
google_gcm_sender_id = 509878466986  # Change this to your gcm sender id

# Message Queueing, this should be the relay. A "sane" value
# for this would be something like ipc:///tmp/pushrocket-relay.ipc
zeromq_relay_uri = ''
