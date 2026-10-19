-- Generated from legal_abduction/repository.py TABLES; keep in sync (tested).
-- SQLite dialect (GLOB, json_valid, RAISE triggers); PostgreSQL port: LA-022/LA-030.
CREATE TABLE meta (case_id TEXT NOT NULL PRIMARY KEY, schema_version INTEGER NOT NULL);
CREATE TABLE runs (case_id TEXT NOT NULL, id TEXT NOT NULL CHECK (id GLOB 'run:?*'), corpus_hash TEXT NOT NULL, analysis_hash TEXT NOT NULL, render_hash TEXT NOT NULL, approved_set_hash TEXT NOT NULL, code_version TEXT NOT NULL, model_id TEXT NOT NULL, runtime TEXT NOT NULL, parent_run_id TEXT, PRIMARY KEY (case_id, id), FOREIGN KEY (case_id, parent_run_id) REFERENCES runs (case_id, id));
CREATE TABLE steps (case_id TEXT NOT NULL, id TEXT NOT NULL CHECK (length(id) > 0), run_id TEXT NOT NULL, name TEXT NOT NULL CHECK (length(name) > 0), agent TEXT NOT NULL CHECK (agent GLOB 'software:?*' OR agent GLOB 'model:?*' OR agent GLOB 'human:?*' OR agent = 'none'), PRIMARY KEY (case_id, id), FOREIGN KEY (case_id, run_id) REFERENCES runs (case_id, id));
CREATE TABLE documents (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'doc:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
  kind TEXT NOT NULL CHECK (kind IN ('original', 'derived')),
  derived_from TEXT,
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id),
  CHECK (kind = 'original' OR derived_from IS NOT NULL)
);
CREATE TABLE passages (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'psg:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  document_id TEXT NOT NULL,
  text_sha256 TEXT NOT NULL CHECK (length(text_sha256) = 64),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id),
  FOREIGN KEY (case_id, document_id) REFERENCES documents (case_id, id)
);
CREATE TABLE family_memberships (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  document_id TEXT NOT NULL,
  family_id TEXT NOT NULL CHECK (length(family_id) > 0),
  basis TEXT NOT NULL CHECK (basis IN ('bytes', 'email_headers', 'human')),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id),
  FOREIGN KEY (case_id, document_id) REFERENCES documents (case_id, id)
);
CREATE TABLE event_time_assessments (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  observation_id TEXT NOT NULL,
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE search_records (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  corpus_hash TEXT NOT NULL CHECK (length(corpus_hash) = 64),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE value_records (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE claims (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'clm:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  speaker_role TEXT NOT NULL CHECK (speaker_role IN ('party', 'subject', 'witness', 'third', 'system')),
  epistemic_status TEXT NOT NULL CHECK (epistemic_status <> 'established' AND length(epistemic_status) > 0),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE observation_sets (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'set:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE observations (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'obs:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE perspectives (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'per:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  role TEXT NOT NULL CHECK (role IN ('party', 'subject', 'organization', 'third_party')),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE hypotheses (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'hyp:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  kind TEXT NOT NULL CHECK (kind IN ('substantive', 'process', 'data_error', 'mixed', 'other_unrecognized')),
  status TEXT NOT NULL CHECK (status IN ('hypothesis')),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE assumptions (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'asm:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  kind TEXT NOT NULL CHECK (kind IN ('bridge_rule', 'background', 'model_assumed')),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE assessments (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'ass:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  observation_id TEXT NOT NULL,
  hypothesis_id TEXT NOT NULL,
  relation TEXT NOT NULL CHECK (relation IN ('supports', 'conflicts', 'neutral')),
  supersedes TEXT,
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id),
  FOREIGN KEY (case_id, observation_id) REFERENCES observations (case_id, id),
  FOREIGN KEY (case_id, hypothesis_id) REFERENCES hypotheses (case_id, id),
  FOREIGN KEY (case_id, supersedes) REFERENCES assessments (case_id, id)
);
CREATE TABLE tests (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'tst:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE reviews (
  case_id TEXT NOT NULL,
  id TEXT NOT NULL CHECK (length(id) BETWEEN 1 AND 140 AND id GLOB 'rev:?*'),
  body_json TEXT NOT NULL CHECK (json_valid(body_json)),
  item_id TEXT NOT NULL CHECK (length(item_id) > 0),
  decision TEXT NOT NULL CHECK (length(decision) > 0),
  reviewer TEXT NOT NULL CHECK (length(reviewer) > 0),
  evidence_class TEXT NOT NULL CHECK (length(evidence_class) > 0),
  created_step_id TEXT NOT NULL,
  PRIMARY KEY (case_id, id),
  FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id)
);
CREATE TABLE prov_edges (case_id TEXT NOT NULL, id TEXT NOT NULL, subject_id TEXT NOT NULL CHECK (subject_id GLOB '?*:?*'), predicate TEXT NOT NULL CHECK (predicate IN ('wasGeneratedBy', 'wasDerivedFrom', 'wasAttributedTo', 'wasInformedBy', 'used', 'wasInvalidatedBy')), object_id TEXT NOT NULL CHECK (object_id GLOB '?*:?*'), step_id TEXT NOT NULL, PRIMARY KEY (case_id, id), FOREIGN KEY (case_id, step_id) REFERENCES steps (case_id, id));
CREATE TABLE proposals (case_id TEXT NOT NULL, id TEXT NOT NULL CHECK (length(id) > 0), task_type TEXT NOT NULL CHECK (length(task_type) > 0), cache_key TEXT NOT NULL, payload_json TEXT NOT NULL CHECK (json_valid(payload_json)), created_step_id TEXT NOT NULL, PRIMARY KEY (case_id, id), FOREIGN KEY (case_id, created_step_id) REFERENCES steps (case_id, id));
CREATE TABLE chain (case_id TEXT NOT NULL, seq INTEGER NOT NULL CHECK (seq >= 1), table_name TEXT NOT NULL, row_id TEXT NOT NULL, row_hash TEXT NOT NULL CHECK (length(row_hash) = 64), prev_hash TEXT NOT NULL CHECK (length(prev_hash) = 64), PRIMARY KEY (case_id, seq), UNIQUE (case_id, table_name, row_id));
CREATE TABLE run_heads (case_id TEXT NOT NULL, run_id TEXT NOT NULL, seq INTEGER NOT NULL CHECK (seq >= 0), chain_head TEXT NOT NULL CHECK (length(chain_head) = 64), PRIMARY KEY (case_id, run_id, seq), FOREIGN KEY (case_id, run_id) REFERENCES runs (case_id, id));
CREATE TABLE checkpoints (case_id TEXT NOT NULL, step_id TEXT NOT NULL, batch_no INTEGER NOT NULL, record_json TEXT NOT NULL CHECK (json_valid(record_json)), PRIMARY KEY (case_id, step_id, batch_no));
CREATE VIEW current_assessments AS SELECT a.* FROM assessments a WHERE NOT EXISTS (SELECT 1 FROM assessments b WHERE b.case_id = a.case_id AND b.supersedes = a.id);
CREATE VIEW proposal_state AS SELECT p.case_id, p.id, COALESCE((SELECT r.decision FROM reviews r WHERE r.case_id = p.case_id AND r.item_id = p.id ORDER BY r.rowid DESC LIMIT 1), CASE WHEN n.k = 0 THEN 'pending' WHEN n.k >= COALESCE(json_array_length(json_extract(p.payload_json, '$.items')), 0) THEN 'reviewed' ELSE 'partially_reviewed' END) AS state FROM proposals p JOIN (SELECT p2.case_id AS cid, p2.id AS pid, (SELECT count(DISTINCT r2.item_id) FROM reviews r2 WHERE r2.case_id = p2.case_id AND substr(r2.item_id, 1, length(p2.id) + 1) = p2.id || '#') AS k FROM proposals p2) n ON n.cid = p.case_id AND n.pid = p.id;
CREATE VIEW runs_current AS SELECT r.*, (SELECT h.chain_head FROM run_heads h WHERE h.case_id = r.case_id AND h.run_id = r.id ORDER BY h.rowid DESC LIMIT 1) AS chain_head FROM runs r;
CREATE TRIGGER meta_no_replace BEFORE INSERT ON meta WHEN EXISTS (SELECT 1 FROM meta WHERE case_id = NEW.case_id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER meta_no_update BEFORE UPDATE ON meta BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER meta_no_delete BEFORE DELETE ON meta BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER runs_no_replace BEFORE INSERT ON runs WHEN EXISTS (SELECT 1 FROM runs WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER runs_no_update BEFORE UPDATE ON runs BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER runs_no_delete BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER steps_no_replace BEFORE INSERT ON steps WHEN EXISTS (SELECT 1 FROM steps WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER steps_no_update BEFORE UPDATE ON steps BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER steps_no_delete BEFORE DELETE ON steps BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER documents_no_replace BEFORE INSERT ON documents WHEN EXISTS (SELECT 1 FROM documents WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER documents_no_update BEFORE UPDATE ON documents BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER documents_no_delete BEFORE DELETE ON documents BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER passages_no_replace BEFORE INSERT ON passages WHEN EXISTS (SELECT 1 FROM passages WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER passages_no_update BEFORE UPDATE ON passages BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER passages_no_delete BEFORE DELETE ON passages BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER family_memberships_no_replace BEFORE INSERT ON family_memberships WHEN EXISTS (SELECT 1 FROM family_memberships WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER family_memberships_no_update BEFORE UPDATE ON family_memberships BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER family_memberships_no_delete BEFORE DELETE ON family_memberships BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER event_time_assessments_no_replace BEFORE INSERT ON event_time_assessments WHEN EXISTS (SELECT 1 FROM event_time_assessments WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER event_time_assessments_no_update BEFORE UPDATE ON event_time_assessments BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER event_time_assessments_no_delete BEFORE DELETE ON event_time_assessments BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER search_records_no_replace BEFORE INSERT ON search_records WHEN EXISTS (SELECT 1 FROM search_records WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER search_records_no_update BEFORE UPDATE ON search_records BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER search_records_no_delete BEFORE DELETE ON search_records BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER value_records_no_replace BEFORE INSERT ON value_records WHEN EXISTS (SELECT 1 FROM value_records WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER value_records_no_update BEFORE UPDATE ON value_records BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER value_records_no_delete BEFORE DELETE ON value_records BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER claims_no_replace BEFORE INSERT ON claims WHEN EXISTS (SELECT 1 FROM claims WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER claims_no_update BEFORE UPDATE ON claims BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER claims_no_delete BEFORE DELETE ON claims BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER observation_sets_no_replace BEFORE INSERT ON observation_sets WHEN EXISTS (SELECT 1 FROM observation_sets WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER observation_sets_no_update BEFORE UPDATE ON observation_sets BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER observation_sets_no_delete BEFORE DELETE ON observation_sets BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER observations_no_replace BEFORE INSERT ON observations WHEN EXISTS (SELECT 1 FROM observations WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER observations_no_update BEFORE UPDATE ON observations BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER observations_no_delete BEFORE DELETE ON observations BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER perspectives_no_replace BEFORE INSERT ON perspectives WHEN EXISTS (SELECT 1 FROM perspectives WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER perspectives_no_update BEFORE UPDATE ON perspectives BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER perspectives_no_delete BEFORE DELETE ON perspectives BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER hypotheses_no_replace BEFORE INSERT ON hypotheses WHEN EXISTS (SELECT 1 FROM hypotheses WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER hypotheses_no_update BEFORE UPDATE ON hypotheses BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER hypotheses_no_delete BEFORE DELETE ON hypotheses BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER assumptions_no_replace BEFORE INSERT ON assumptions WHEN EXISTS (SELECT 1 FROM assumptions WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER assumptions_no_update BEFORE UPDATE ON assumptions BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER assumptions_no_delete BEFORE DELETE ON assumptions BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER assessments_no_replace BEFORE INSERT ON assessments WHEN EXISTS (SELECT 1 FROM assessments WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER assessments_no_update BEFORE UPDATE ON assessments BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER assessments_no_delete BEFORE DELETE ON assessments BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER tests_no_replace BEFORE INSERT ON tests WHEN EXISTS (SELECT 1 FROM tests WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER tests_no_update BEFORE UPDATE ON tests BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER tests_no_delete BEFORE DELETE ON tests BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER reviews_no_replace BEFORE INSERT ON reviews WHEN EXISTS (SELECT 1 FROM reviews WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER reviews_no_update BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER prov_edges_no_replace BEFORE INSERT ON prov_edges WHEN EXISTS (SELECT 1 FROM prov_edges WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER prov_edges_no_update BEFORE UPDATE ON prov_edges BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER prov_edges_no_delete BEFORE DELETE ON prov_edges BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER proposals_no_replace BEFORE INSERT ON proposals WHEN EXISTS (SELECT 1 FROM proposals WHERE case_id = NEW.case_id AND id = NEW.id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER proposals_no_update BEFORE UPDATE ON proposals BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER proposals_no_delete BEFORE DELETE ON proposals BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER chain_no_replace BEFORE INSERT ON chain WHEN EXISTS (SELECT 1 FROM chain WHERE case_id = NEW.case_id AND seq = NEW.seq) OR EXISTS (SELECT 1 FROM chain WHERE case_id = NEW.case_id AND table_name = NEW.table_name AND row_id = NEW.row_id) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER chain_no_update BEFORE UPDATE ON chain BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER chain_no_delete BEFORE DELETE ON chain BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER run_heads_no_replace BEFORE INSERT ON run_heads WHEN EXISTS (SELECT 1 FROM run_heads WHERE case_id = NEW.case_id AND run_id = NEW.run_id AND seq = NEW.seq) BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER run_heads_no_update BEFORE UPDATE ON run_heads BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
CREATE TRIGGER run_heads_no_delete BEFORE DELETE ON run_heads BEGIN SELECT RAISE(ABORT, 'E_IMMUTABLE'); END;
