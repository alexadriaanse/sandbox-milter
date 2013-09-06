sandbox-milter
==============

The purpose of this milter is to trap and redirect certain emails.  This is
useful for a development environment, where certain emails that are sent out by
accident, e.g. to real customers, are redirected to a developer's email address.

sandbox-milter provides both an "smtpd" and "nonsmtpd" milter.  The type of
milter that is started is determined through a command-line argument.


Prerequisites
-------------

- Python 2.7 (provided by the Debian python2.7 package)
- Python milter (provided by the Debian python-milter package)

This milter has been tested with Postfix 2.7 on Debian Linux 7.1.


Example postfix configuration
-----------------------------

    milter_default_action = accept
    non_smtpd_milters = unix:/milter/sandbox_nonsmtpd_milter.sock
    smtpd_milters = unix:/milter/sandbox_smtpd_milter.sock
    milter_protocol = 6

Note: Postfix is chrooted on Debian by default chrooted, so be sure to keep
that in mind when configuring the milter socket paths


Usage
-----

    sandbox_milter.py smtpd
    sandbox_milter.py nonsmtpd

Output is logged to the mail.info and/or mail.debug syslog facilities


Configuration
-------------

The `valid_senders` file contains a list of legitimate senders whose emails are
*not* redirected *iff* sent through SMTP.

The `allowed_recipients` file contains a list of recipients whose emails are never
redirected to `redirect_address`.  This usually contains a list of development
and test user email addresses.  This file can contain both emails and domains
(in the form of "@domain.tld").

Neither `valid_senders` nor `allowed_recipients` files should contain any comments
or anything other than email addresses or domains.

The `valid_senders` and `allowed_recipients` files are re-read upon each email
delivery, so changes to these two files do not require sandbox-milter to be
restarted.  The text format that is used in both files causes the milter to not
scale well when these two files grow large.  Should this be the case, these
files should be turned into database or hash files.

Changes to `sandbox_milter.cfg` will require sandbox-milter to be restarted in
order for these changes to take effect.


Rules implemented by sandbox-milter
-----------------------------------

Redirect email to `redirect_address` unless:

1. Envelope sender email address is in `valid_senders` list *and* email is sent through SMTP, or
2. Envelope recipient email address or domain is in `allowed_recipients`


Installation
------------

1. Create a milter group, and add the postfix user to it
2. Create a milter user, and assign it to the milter group
3. Copy or symlink `sandbox_milter.rc` to `/etc/init.d/sandbox_milter`
4. Execute: `update-rc.d sandbox_milter defaults`
