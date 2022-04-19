# NZSL-signbank

**Manage your sign language lexicons.**

NZSL-signbank is a web based database for **sign language** lexicons and corpuses.
Sign language annotation will be easier, faster, and more accurate.

# Overview

NZSL-signbank is being developed as a successor to an existing legacy system that is no longer maintained. It is based
on [Global Signbank](https://github.com/Signbank/Global-signbank) and aims to be able to contribute features and improvements upstream.

Main features:

- Manage and organize sign language lexicons and corpuses.
- Store multiple lexicons of different sign languages.
- Use your Glosses in [ELAN][elan-link] with ECV (externally controlled dictionary).
  - ECV's are available for all lexicons automatically.
- Upload videos and connect them to glosses.
- Add comments on glosses and tag them.
- Store relationships between glosses, view a network graph of these relationships.
- Interface easily translatable to multiple languages.
- Control access to lexicons per user/group.
- Publish lexicons and their glosses.
  - Separate interface for published glosses, detailed interface for researchers/annotators.
- Add translation equivalents to your glosses in any language.

# Requirements

Running the app in Docker using docker-compose is recommended, but not mandatory.

To start the application using docker-compose, simply run:

`docker-compose up`

And the service will start bound to port 8000 on your host.

You may wish to run `docker-compose run backend ./bin/develop.py prefill_database` to set up an admin user, and an initial dataset.

To run the application locally you will need:

- Python 3 (3.6+ recommended)
- Pip
- LibXML
- AVConv (or FFMPEG symlinked to avconv)
- https://github.com/vanlummelhuizen/CNGT-scripts cloned into your repository
- Either PostgreSQL client libraries or SQLite (we use Postgres, but Global-signbank uses SQLite and this should continue to be supported)

Dependencies can be found in [requirements.txt][requirements.txt] and they can be installed using pip: `pip install -r requirements.txt`.
Once you have the application set up locally, you can run `./bin/develop.py prefill_database` to set up an admin user and an initial dataset.

# Contribution

If you want to contribute to the project, please open an issue describing the problem or feature you would be interested in contributing towards so that we can provide help and guidance.
NZSL has funding goals and objectives to meet, so contributions will sometimes be scheduled or adjusted to align with our own delivery schedule.

[requirements.txt]: https://github.com/odnzsl/NZSL-signbank/blob/main/requirements.txt
[elan-link]: https://archive.mpi.nl/tla/elan/
