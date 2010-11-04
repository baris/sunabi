#!/usr/bin/python
# Baris Metin <baris !! metin.org>

import sys
import os
import getpass
from twisted.words.xish import domish
from twisted.internet import reactor, task
from twisted.words.protocols.jabber import xmlstream, client, jid

XMPP_SERVER = "jabber.fr"
XMPP_USER = "USER@jabber.fr"
XMPP_PASSWORD = getpass.getpass("jabber password: ")
ADMINS = ['admin@jabber.fr', 'admin2@jabber.org']


GET_COMMANDS = { 
    "ps" : "ps auxww",
    "uptime" : "uptime",
    "uname" : "uname -a"
    }


def run(command):
    def _run(cmd):
        return os.popen("%s 2> /dev/null" % cmd).read()
    try:
        return _run(GET_COMMANDS[command])
    except:
        return "Available commands: %s" % ",".join(GET_COMMANDS.keys())



class BaseClient(object):
    """ Base XMPP client: handles authentication and basic presence/message requests. """
    def __init__(self, id, secret, verbose = False, log = None):

        if isinstance(id, (str, unicode)):
            id = jid.JID(id)
        x = client.XMPPClientFactory(id, secret)
        x.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.event_connected)
        x.addBootstrap(xmlstream.STREAM_END_EVENT, self.event_disconnected)
        x.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.event_init_failed)
        x.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.event_authenticated)
        self.id = id
        self.factory = x
        self.verbose = verbose
        self.log = log or sys.stdout

    def __rawDataIN(self, buf):
        if self.verbose: self.msg("RECV: %s" % buf)

    def __rawDataOUT(self, buf):
        if self.verbose: self.msg("SEND: %s" % buf)

    def msg(self, msg):
        self.log.write("%s\n" % msg)
        self.log.flush()

    def error(self, msg):
        self.msg("ERROR: %s" % msg)

    def warn(self, msg):
        self.msg("WARN: %s" % msg)

    def info(self, msg):
        self.msg("INFO: %s" % msg)

    def event_connected(self, xs):
        # log all traffic
        xs.rawDataInFn = self.__rawDataIN
        xs.rawDataOutFn = self.__rawDataOUT
        self.xmlstream = xs
        
    def event_disconnected(self, xs):
        pass

    def event_init_failed(self, xs):
        self.error("Init Failed")

    def event_authenticated(self, xs):
        presence = domish.Element(("jabber:client", "presence"))
        presence.addElement("show", content="dnd")
        presence.addElement("status", content="man at work")
        xs.send(presence)

        # add protocol handlers
        xs.addObserver("/presence[@type='subscribe']", self.presence_subscribe)
        xs.addObserver("/presence[@type='unsubscribe']", self.presence_unsubscribe)
        xs.addObserver("/precence", self.presence)
        xs.addObserver("/message[@type='chat']", self.message_chat)

    def presence_subscribe(self, m):
        self.info("%s request to add us, granting." % m['from'])
        p = domish.Element(("jabber:client", "presence"))
        p['from'], p['to'] = m['to'], m['from']
        p['type'] = "subscribed"
        self.xmlstream.send(p)

    def presence_unsubscribe(self, m):
        # try to re-subscribe
        self.info("%s removed us, trying to re-authenticate." % m['from'])
        p = domish.Element(("jabber:client", "presence"))
        p['from'], p['to'] = m['to'], m['from']
        p['type'] = "subscribe"
        self.xmlstream.send(p)

    def presence(self, m):
        p = domish.Element(("jabber:client", "presence"))
        p['from'], p['to'] = m['to'], m['from']
        presence.addElement("show", content="dnd")
        presence.addElement("status", content="man at work")
        self.xmlstream.send(p)

    def message_chat(self, m):
        body = ""
        for e in m.elements():
            if e.name == "body":
                body = "%s" % e
                break
        reply = run(body)

        n = domish.Element((None, "message"))
        n['to'], n['from'] = m['from'], self.id.full()
        n.addElement("body", content = reply)
        self.xmlstream.send(n)


    # just for testing.
    def check_httpd(self):
        running = False
        lines = os.popen("ps auxww 2> /dev/null | grep httpd").readlines()
        for line in lines:
            if line.find("/usr/sbin/httpd") >= 0:
                running = True
                break

        if not running:
            for admin in ADMINS:
                n = domish.Element((None, "message"))
                n['to'], n['from'] = admin, self.id.full()
                n.addElement("body", content = "httpd stopped running on 'bizim sunucu'!")
                self.xmlstream.send(n)


if __name__ == "__main__":
    sunabi = BaseClient(XMPP_USER, XMPP_PASSWORD, verbose=False)

    t = task.LoopingCall(sunabi.check_httpd)
    t.start(15.0 * 60) # check every 15 minutes

    reactor.connectTCP(XMPP_SERVER, 5222, sunabi.factory)
    reactor.run(installSignalHandlers=True)



