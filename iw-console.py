"""
Very simple console client for Instawallet.
(note: in particular proper error handling
for some aspects is missing)
"""

import os
import os.path
import urllib
import json
import socket
import re
import select
import sys

API_URL = 'https://www.instawallet.org/api/v1/'
LINE_DELIMITER = '\r\n'

def call_api(url_suffix, data = None):
    f = urllib.urlopen(API_URL + url_suffix, data)
    data = f.read()
    return json.loads(data)

def execute_cmd(cmd, wallet_id):
    if not cmd.startswith('payment'):
        return "Command not recognized"

    params = cmd.split(" ")
    if not len(params) > 2:
        return "Not enough parameters"
    try:
        address = params[1]
        amount = long(float(params[2]) * 10**8)
    except ValueError:
        return "Unable to parse amount"

    post_data = urllib.urlencode({'address': address, 'amount': amount})
    result = call_api('w/%s/payment' % wallet_id, post_data)
    return result['message']

def format_btc_amount(amount):
    s = "%.8f" % (float(amount) / 10**8)
    return re.sub("\.?0+$", "", s)

# check for configuration file
conffile = os.path.join(os.environ['HOME'], '.iw-console')
if os.path.isfile(conffile):
    with open(conffile, 'r') as f:
        wallet_id = f.readline().strip()
else:
    # looks like no configuration exists -> create new wallet
    wallet_id = call_api('new_wallet')['wallet_id']
    with open(conffile, 'w') as f:
        f.write("%s\n" % wallet_id)

# output info
print "Using http://www.instawallet.org/w/%s" % wallet_id
print "Bitcoin address is: %s" % call_api('w/%s/address' % wallet_id)['address']
print "To do a payment try: payment <address> <amount in BTC>"

# subscribe to balance updates
subscription_id = call_api('w/%s/subscription' % wallet_id)['subscription_id']
request = json.dumps({'subscription_id': subscription_id})
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('www.instawallet.org', 8202))
s.send(request + LINE_DELIMITER)

# enter select loop: check both for keyboard
# input and balance updates on the socket
while True:
    i, _, _ = select.select([sys.stdin, s], [], [])
    for iready in i:
        if iready == sys.stdin:
            cmd = sys.stdin.readline().strip()
            print execute_cmd(cmd, wallet_id)
        else:
            _ = iready.recv(4096)   # don't care about payload,
                                    # we know it was a 'ping'
            balance = call_api('w/%s/balance' % wallet_id)['balance']
            print "Balance: %s BTC" % format_btc_amount(balance)
