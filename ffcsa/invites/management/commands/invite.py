"""
Management utility to create invitation codes

Eg. python manage.py invite --domain=mysite.com

"""

from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse
from django.db import DEFAULT_DB_ALIAS
from django.utils.encoding import force_str
from django.contrib.sites.models import Site

from invites.models import InvitationCode
from invites.utils import send_invite_code_mail


class Command(BaseCommand):
    help = 'Create an Invite Code'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            dest='email',
            help="The email address of the invitee",
        )
        parser.add_argument(
            '--domain',
            dest='domain',
            help="The site's url root domain"
        )
        parser.add_argument(
            '--database',
            action='store',
            dest='database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".'
        )
        parser.add_argument(
            '--noinput',
            action='store_false',
            dest='interactive',
            default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'
        )
        parser.add_argument(
            '--send',
            action='store_true',
            dest='send',
            default=False,
            help='Send the Invite Code to the invitee right away.'
        )
        parser.add_argument(
            '--https',
            action='store_true',
            dest='https',
            default=False,
            help="The site urls within the sent email should use 'https'"
        )

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1))
        database = options.get('database')
        email = options.get('email')
        domain = options.get('domain')
        interactive = options.get('interactive')
        send = options.get('send')
        https = options.get('https')
        sites = Site.objects.all()
        site_items = dict((str(obj.id), obj) for obj in sites)
        site = None
        if not site_items:
            raise CommandError("No site available.")
        while not email:
            if not interactive:
                raise CommandError("Missing parameter 'email'")
            email = (input(
                force_str('Enter the email address of the recipient: ')
            ) or '').strip()
        if domain:
            for site in sites:
                if site.domain == domain:
                    break
            else:
                raise CommandError("A site with domain '%s' does not exist" % domain)
        else:
            if len(site_items) == 1:
                site = sites[0]
            while site is None:
                if not interactive:
                    raise CommandError("Missing parameter 'domain'")
                for obj in sites:
                    self.stdout.write("[%s] %s" % (obj.id, obj.domain))
                site_id = input(force_str('Select a site: '))
                try:
                    site = site_items[site_id]
                except KeyError:
                    continue
        code = InvitationCode.objects.create_invite_code(email, site=site)
        do_send = None
        while do_send is None:
            if not interactive:
                do_send = 'y' if send else 'n'
                break
            do_send = (input(
                force_str('Send the code now? [y/N]')
            ) or '').strip().lower()
            do_send = do_send or 'n'
            if do_send not in 'yn':
                do_send = None
        if do_send == 'y':
            secure = None
            while secure is None:
                if not interactive:
                    secure = 'y' if https else 'n'
                    break
                secure = (input(
                    force_str('Use https for site urls in the email? [y/N]')
                ) or '').strip().lower()
                secure = secure or 'n'
                if secure not in 'yn':
                    secure = None
            protocol = 'http'
            if secure == 'y':
                protocol += 's'
            site_url = '%s://%s%s' % (protocol, site.domain, reverse("home"))
            display_signup_url = '{}://{}{}'.format(protocol, site.domain, reverse("mezzanine_signup"))
            signup_url = '{url}?email={email}&code={code}'.format(url=display_signup_url, email=code.registered_to,
                                                                  code=code.short_key)
            try:
                send_invite_code_mail(code, site_url, display_signup_url, signup_url)
            except Exception as e:
                self.stderr.write("Mail send error - %s" % e)
                return
            else:
                self.stdout.write("Mail sent to %s." % code.registered_to)
        else:
            self.stdout.write(code.short_key)
