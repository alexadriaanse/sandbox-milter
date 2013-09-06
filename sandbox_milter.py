#!/usr/bin/python2.7

import sys
import os
import Milter
import ConfigParser
import logging
import logging.handlers
import re

class SandboxMilter(Milter.Milter):
    """
    Milter to rewrite the envelope FROM and RCPT addresses depending on
    whether they should escape the sandbox
    """

    def __init__(self):
        self.initEnvelope()
        self.logger = logger

    def initEnvelope(self):
        """
        Initializes the envelope sender and recipients.  This function is called
        even from within eoh(), just in case this object is recycled between
        multiple requests.
        """
        self.sender = None
        self.recipients = []
        
    def log(self, *msg):
        """
        Passes a log message through logString
        """
        message_str = ' '.join(map(lambda element: str(element), msg))
        self.logString(message_str, logging.DEBUG)

    def logString(self, message, level = logging.INFO):
        """
        Logs a message to syslog
        """
        self.logger.log(level, message)

    def envfrom(self, f, *str):
        """
        Stores the email sender
        """
        Milter.Milter.envfrom(self, f, *str)
        self.sender = f
        return Milter.CONTINUE

    def envrcpt(self, to, *str):
        """
        Stores an email recipient
        """
        Milter.Milter.envrcpt(self, to, *str)
        self.recipients.append(to)
        return Milter.CONTINUE

    def eom(self):
        """
        Rewrites the recipients in the email
        """

        normalize_re = re.compile('^(<?)(.*?)(>?)$')
        match = normalize_re.match(self.sender)
        (_, sender, _) = match.groups()

        if (mode == 'smtpd' and
            lookupKey(config.get('sandbox', 'valid_senders'), sender)):

            # Don't rewrite if valid senders.  This should catch all legitimate
            # emails personally sent using an SMTP client.
            self.initEnvelope()
            return Milter.CONTINUE

        # Rewrite recipients
        redirect_address = config.get('sandbox', 'redirect_address')
        for recipient in self.recipients:
            # Check whether recipient has been whitelisted.  First check domain
            # (@domain.tld), then check individual email addresses
            match = normalize_re.match(recipient)
            (prefix, recipient_email, suffix) = match.groups()
            recipient_parts = recipient_email.rsplit('@', 1)
            if (len(recipient_parts) != 2):
                # Recipient doesn't have a domain, so it's a local recipient
                # which we never redirect
                continue

            domain_part = '@' + recipient_parts[1]
            if (lookupKey(config.get('sandbox', 'allowed_recipients'), domain_part)):
                # Don't redirect email
                continue
            if (lookupKey(config.get('sandbox', 'allowed_recipients'), recipient_email)):
                # Don't redirect email
                continue

            # Redirect email

            self.logString("Redirecting email from %s addressed to %s to %s" %
                (sender, recipient_email, redirect_address))
            self.delrcpt(recipient)
            self.addrcpt(prefix + redirect_address + suffix)

        self.initEnvelope()
        return Milter.CONTINUE

def lookupKey(file, key):
    with open(file, 'r') as db:
        lines = db.readlines();
        for line in lines:
            value = line.strip()
            if (key.lower() == value.lower()):
                # Key was found
                return True

        # Key was not found
        return False

if (__name__ == "__main__"):
    os.umask(0002)

    if (len(sys.argv) != 2):
        print('Usage: %s MODE' % sys.argv[0])
        print('Where MODE is smtpd or nonsmtpd')
        exit(1)

    if (sys.argv[1] not in ['smtpd', 'nonsmtpd']):
        print('%s is not a valid mode' % sys.argv[1])
        exit(1)

    mode = sys.argv[1]
    Milter.factory = SandboxMilter
    Milter.set_flags(Milter.ADDRCPT + Milter.DELRCPT)

    config = ConfigParser.SafeConfigParser()
    config.read('/etc/sandbox_milter/sandbox_milter.cfg')

    milter_section = mode + "_milter"
    socket = config.get(milter_section, 'socket')
    name = config.get(milter_section, 'socket')

    # Initialize logging
    logger = logging.getLogger('')
    if (config.getboolean('sandbox', 'log_debug')):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    handler = logging.handlers.SysLogHandler(
        address = '/dev/log',
        facility = logging.handlers.SysLogHandler.LOG_MAIL)
    formatter = logging.Formatter('sandbox_milter[%(process)d]: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    Milter.runmilter(name, socket, 0)
