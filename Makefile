
all: build

build:
	docker build -f Dockerfile -t ethburnbot .


db_delete:
	sudo rm -rf data/postgresql
	mkdir data/postgresql
	docker rm -f ethburnbot_postgres

db: db_delete
	docker-compose -f docker/docker-compose.yaml up --force-recreate

psql:
	docker exec -it ethburnbot_postgres psql -U postgres

lint:
	./bin/lint.sh

