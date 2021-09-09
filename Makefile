
all: build

build:
	docker build -f Dockerfile -t ethburnbot .

