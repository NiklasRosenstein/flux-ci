'''
This is the Flux configuration file.
'''

host = ''
port = 4042
debug = True

# Full path to the SSH identity file, or None to let SSH decide.
ssh_identity_file = None

# Dictionary to configure accepted repositories. Example:
#
#   'gildarts/awesome-app': {
#     'secret': 'your-secret-key',
#     'clone_url': 'git@gildarts-web.com:gildarts/awesome-app.git',
#     'ssh_identity_file': '/home/buildserver/.ssh/id_rsa'  # optional
#   }
#
repos = {
}
