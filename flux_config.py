'''
This is the Flux configuration file.
'''

host = ''
port = 4042
debug = True

# Full path to the SSH identity file, or None to let SSH decide.
# This option can also be overwritten on a per-repository basis.
ssh_identity_file = None

# Dictionary to configure accepted repositories. The secret is
# either provided by the webhook registrar or it allows you to
# specify a secret manually. In case of the latter, you can
# generate a new secret with the `flux_secret.py` script.
#
# Example configuration:
#
#   'gildarts/awesome-app': {
#     'secret': 'your-secret-key',
#     'clone_url': 'git@gildarts-web.com:gildarts/awesome-app.git',
#     'ssh_identity_file': '/home/buildserver/.ssh/id_rsa'  # optional
#   }
#
repos = {
}
