# inChat (Onlim) credentials for POST /inchat/sync and InGraphInChatComunication.py.
#
# Copy this file to config.py (gitignored and dockerignored, never commit it) and fill it in.
# Alternatively set the environment variables INCHAT_API_KEY, INCHAT_PUBLISHER and
# INCHAT_DATASOURCE (e.g. in a .env file next to docker-compose.yml): they take
# precedence over config.py. While any of the three is empty, nothing is sent.

API_KEY = ""
PUBLISHER = ""
DATASOURCE = ""
