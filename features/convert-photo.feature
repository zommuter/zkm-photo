# zkm-photo key journeys. The plugin has no UI of its own — it is driven via
# the zkm core CLI — so all scenarios are @manual human-checklist Gherkin
# (run against a scratch store: ZKM_STORE=/tmp/photo-kb).

@manual
Feature: Import photos into the knowledge store
  As a zkm user
  I want my photo directory converted into searchable markdown
  So that photos show up in zkm search next to mail and notes

  Background:
    Given a scratch store initialised with "zkm init"
    And zkm-config.yaml contains a "photo:" section with "source_dir" pointing
      at a directory of real JPEGs (some with GPS, some scans without EXIF)

  Scenario: First ingest
    When I run "zkm convert photo"
    Then a markdown file appears under photos/YYYY/MM/ for each distinct photo
    And each frontmatter has source/date/tags/sha256/processor/processor_version
    And GPS photos carry "location" as signed decimal degrees
    And the original bytes live under originals/photos/_objects/
    And inbox/photos/YYYY/MM/ holds one symlink per photo with an .origin.json sidecar beside it
    And the store git log shows one auto-commit scoped to the plugin's dirs

  Scenario: Re-run is a no-op
    When I run "zkm convert photo" a second time without adding photos
    Then it reports zero new files
    And no CAS object, markdown file, or sidecar producer entry is added

  Scenario: Photo shared with an email attachment gains a second producer
    Given a JPEG that was already ingested as a zkm-eml attachment
    When I run "zkm convert photo" over a directory containing the same JPEG
    Then inbox/photos/YYYY/MM/ still has exactly one symlink for those bytes
    And its .origin.json lists both "eml" and "photo" producers

  Scenario: Photos are searchable
    Given "zkm convert photo" and "zkm index" have run
    When I run "zkm search <camera model or filename slug>"
    Then the photo's markdown file appears in the results

  Scenario: Real-camera HEIC (gate for roadmap:4514 sign-off)
    Given an iPhone .heic photo with EXIF capture date and GPS
    When I run "zkm convert photo"
    Then the markdown frontmatter carries the EXIF date (not file mtime)
    And location is present in signed decimal degrees
