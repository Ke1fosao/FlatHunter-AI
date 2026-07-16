# Stage 7 — Duplicate Detection and Listing Clusters

Stage 7 prevents the same apartment from appearing as several independent cards when it is reposted or published by multiple approved sources.

## User-facing behavior

The default feed, personalized matches, favorites, comparison, dashboard, and map return:

- standalone listings; and
- one primary listing for every active duplicate cluster.

A clustered card contains:

- `cluster_id`;
- `member_count` and distinct `source_count`;
- `price_min_uah` and `price_max_uah`;
- one cluster-aware favorite, hidden, compared, and note state;
- a detail view with every source copy and direct source link.

All original `Listing` rows remain stored. Clustering never deletes or rewrites source-normalized records.

## Pipeline

```text
Listing create/update
→ ListingFingerprint
→ bounded candidate blocks
→ explainable duplicate score
→ auto merge / review / reject
→ guarded cluster rebuild
→ deterministic primary selection
→ cluster-aware API and Mini App
```

The pipeline is deterministic and idempotent for unchanged inputs.

## Fingerprints

`ListingFingerprint` stores only normalized or hashed evidence:

- canonical URL;
- normalized city, district, street, title, and description;
- address, geospatial, attribute, price, and text block keys;
- 64-bit SimHash;
- SHA-256 contact hashes;
- trusted exact/perceptual image metadata.

Raw contacts are not copied to duplicate tables.

Normal API reads never download remote images. The Stage 7 image command only refreshes trusted imported metadata and deterministic demo hashes.

## Candidate generation

The detector does not compare every listing with every other listing. Candidate pairs must share at least one bounded block:

- canonical URL;
- hashed contact;
- normalized address;
- coordinate grid and room count;
- stable attributes and close price bucket;
- trusted exact image hash;
- close text SimHash inside the same city.

Hard conflicts reject a pair before clustering, including different city, deal type, property type, strongly incompatible room count/area, or distant building-accurate coordinates.

## Explainable score

Default weights:

| Component | Weight |
|---|---:|
| exact identifiers / contacts | 25% |
| address / geography | 25% |
| property attributes | 15% |
| normalized text | 15% |
| image evidence | 15% |
| price compatibility | 5% |

Unavailable components are excluded and remaining weights are renormalized. Missing data is never counted as positive evidence.

Default policy:

- score `>= 92`: auto merge when no hard conflict or manual block exists;
- score `78–91.99`: needs review and remains visible independently;
- score `< 78`: rejected;
- exact compatible URL/contact/multiple-image rules can produce an explainable exact merge.

Thresholds are configurable through environment variables and recorded with the algorithm version.

## Transitive poisoning protection

A simple connected component can incorrectly merge A with C only because both resemble B. Stage 7 prevents this:

- clusters of up to five listings require a complete compatibility graph;
- larger clusters require every member to match the selected primary and at least 70% of all pair relationships to be compatible;
- any manual split/block edge prevents the pair from sharing an active cluster.

## Primary selection

The primary listing is selected deterministically by:

1. active status;
2. approved and healthy source;
3. building-level location accuracy;
4. image count;
5. field completeness;
6. owner preference;
7. lower commission;
8. publication freshness;
9. last-seen freshness;
10. stable UUID tie-breaker.

Changing the primary does not change an existing cluster ID when the component remains the same.

## Manual decisions

Staff can confirm, split/block, or restore automatic policy through Django Admin and protected API actions. `DuplicateDecision` is append-only audit history. A split remains authoritative until restored.

## Management commands

```bash
python manage.py build_listing_fingerprints
python manage.py detect_listing_duplicates
python manage.py rebuild_listing_clusters
python manage.py process_listing_image_hashes
```

Examples:

```bash
python manage.py build_listing_fingerprints --city Львів --limit 500
python manage.py detect_listing_duplicates --listing-id <uuid>
python manage.py detect_listing_duplicates --city Рівне --dry-run
python manage.py rebuild_listing_clusters --city Київ --dry-run
python manage.py process_listing_image_hashes --city Львів
```

Recommended initial rollout:

```bash
python manage.py seed_demo_listings
python manage.py geocode_demo_data
python manage.py build_listing_fingerprints
python manage.py detect_listing_duplicates
python manage.py rebuild_listing_clusters
```

Run the fingerprint/detection/rebuild sequence twice in staging and confirm stable counts before enabling queued incremental refresh.

## API

Cluster detail:

```text
GET /api/v1/listing-clusters/{cluster_id}/
GET /api/v1/listing-clusters/{cluster_id}/?profile_id={profile_id}
```

Cluster state:

```text
PATCH /api/v1/listing-clusters/{cluster_id}/state/
```

Payload supports any subset of:

```json
{
  "is_favorite": true,
  "is_hidden": false,
  "is_compared": true,
  "note": "Уточнити комісію"
}
```

Staff candidate actions:

```text
POST /api/v1/duplicate-candidates/{candidate_id}/confirm/
POST /api/v1/duplicate-candidates/{candidate_id}/split/
POST /api/v1/duplicate-candidates/{candidate_id}/restore/
```

Existing listing, match, dashboard, and map endpoints remain backward compatible and add cluster metadata.

## State semantics

- favorite: one cluster state; the current primary mirrors the legacy listing flag;
- hidden: the whole cluster disappears, including future presentation of existing members;
- compared: one cluster occupies one of the four comparison slots;
- note: stored once on `UserClusterState`;
- standalone listings continue using `UserListingState`.

## Security boundaries

- no LLM decides duplicate identity;
- no unrestricted all-pairs comparison;
- no raw contact persistence in duplicate tables;
- no arbitrary remote image fetching during API requests;
- no user-controlled image provider URL;
- duplicate candidate review actions require staff permissions;
- manual decisions are audited and immutable;
- source approval and enabled status remain mandatory in feeds and candidate generation.

## Monitoring

Track:

- fingerprint failures and stale fingerprints;
- candidate counts by decision and algorithm version;
- auto-merge rate;
- manual split rate after auto merge;
- average cluster size and maximum cluster size;
- rebuild duration;
- clusters without active primary;
- user-state migration/update failures.

A high manual split rate is a signal to raise the auto-merge threshold or tighten candidate blocks.

## Rollback

To disable automatic incremental work without removing data:

```env
DUPLICATE_AUTO_QUEUE_ENABLED=false
```

The original listings remain available. If the cluster presentation layer must be rolled back, archive active clusters and the existing listing records continue to function independently.
