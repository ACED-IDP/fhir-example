

## startup

After cloning this repository:


* start the services
```yaml
docker-compose up -d
```

* install script dependencies 

```yaml
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## usage

* load

```yaml
$ python3 scripts/load.py resources --help
Usage: load.py resources [OPTIONS]

  Load resources (.ndjson).

Options:
  --input_path TEXT     Where to find data to import (json, ndjson)  [default:
                        data/input/resources]

  --url TEXT            url to HAPI FHIR server  [default:
                        http://localhost:8090/fhir]

  --chunk_size INTEGER  Number of simultaneous loaders  [default: 5]
  --help                Show this message and exit.
```

* extract
```yaml
$ python3 scripts/extract.py resources --help
Usage: extract.py resources [OPTIONS]

  Query FHIR resources, write to .ndjson file.

Options:
  --extract_path TEXT  Where to store extracted data (ndjson)  [default:
                       data/output/resources]

  --url_base TEXT      url to HAPI FHIR server [base]  [default:
                       http://localhost:8090/fhir]

  --url_path TEXT      FHIR url path [type]/[id] {?_format=[mime-type]}
                       [default: metadata]

  --help               Show this message and exit.

```

* for example:


```yaml
# download all questionnaire
python3 scripts/extract.py resources --url_path Questionnaire

# download 1 questionnaire
python3 scripts/extract.py resources --url_path Questionnaire?_count=1

# download specific questionnaire
python3 scripts/extract.py resources --url_path Questionnaire?_id=61eb0465b12824010061a35f
```

See https://build.fhir.org/search.html for more


## shutdown

* shutdown services, remove all data permanently (-v)

```yaml
docker-compose down -v
```



### Notes:


* To delete all data in all tables without wiping volumes

```
\c  hapi;
DO $$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE ';
    END LOOP;
END $$;

```



* Had an error creating resources.  I believe the error was "could not execute batch". Traced it to some resources having large base64 documents in DiagnosticReport.presentedFrom

Workaround:

After database is created, log onto postgres:

```
\c hapi;
alter table hfj_res_ver ALTER COLUMN res_text_vc TYPE text ;
```

* If you don't want to use postgres at all, you can use H2, a java based db roughly equivalent to sqlite.

See `datasource` and `jpa.hibernate.dialect` in data/server/application.yaml
