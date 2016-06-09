# Create a virtualenv to deploy flux.
deploy:
	virtualenv -p python3 venv
	venv/bin/pip3 install -r requirements.txt

# Delete the virtualenv created for deployment.
clean:
	rm -rf venv

# Run flux from the virtualenv.
run:
	venv/bin/python3 flux_run.py
