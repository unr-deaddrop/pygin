all: kill run

run:
# Create the `logs` directory (which is assumed based on the directories specified
# in supervisord.conf)
	mkdir -p logs
	supervisord
	python3 -m src.agent_code.main

# Kill supervisord if running (which would be independent of the current window)
# https://stackoverflow.com/questions/7394290/how-to-check-return-value-from-the-shell-directive
# https://unix.stackexchange.com/questions/119648/redirecting-to-dev-null
# https://stackoverflow.com/questions/14479894/stopping-supervisord-shut-down
#
# Also nuke dump.rdb so we have a fresh db each time; this avoids any issues
# due to lingering and will-never-finish tasking
SUPERVISORD_RETVAL := $(shell supervisorctl pid > /dev/null 2>&1; echo $$?)
SUPERVISORD_PID := $(shell supervisorctl pid)
kill:
	rm dump.rdb || true
    ifeq ($(SUPERVISORD_RETVAL),0)
	kill -s SIGTERM $(SUPERVISORD_PID)
	@echo "Killed supervisor - waiting 10 seconds"
	@sleep 10
    else
	@echo "supervisorctl returned nonzero error code, likely not running"
    endif

# Install redis, then install pip requirements
# https://redis.io/docs/install/install-redis/install-redis-on-linux/
# Note that this may not work; redis may be available on the standard package
# distributors, and therefore setting up the package repo may not be necessary.
deps:
	curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
	echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(shell lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
	sudo apt-get update
	sudo apt-get install redis
	pip install -r requirements.txt -U

# To be run on the host or container currently running the DeadDrop server.
#
# This script is the standard entrypoint for the package manager to generate
# the three agent metadata files: agent.json, commands.json, and protocols.json.
# 
# This script should be run immediately after the server decompresses the package,
# after which it can be assumed that all relevant metadata files are available
# (and future metadata files, if any) and can be used to generate the relevant
# models for the Django backend.
install:
	pip3 install -r ./resources/requirements/install-requirements.txt
	python3 -m src.meta.generate_metadata

# To be run *inside* the build container.
payload:
	pip3 install -r ./resources/requirements/payload-requirements.txt
	python3 -m src.meta.generate_config
	apt update
	apt install zip
	rm -rf .git
	zip -r payload.zip .

# To be run *outside* the build container. Note this assumes that the container
# will exit on its own (or else bad things happen!)
payload_entry:
	docker compose -f docker-compose-payload.yml up --build
	docker cp pygin_build:/app/agent_cfg.json ./agent_cfg.json
	docker cp pygin_build:/app/payload.zip ./payload.zip
	docker cp pygin_build:/app/payload-logs.txt ./payload-logs.txt
