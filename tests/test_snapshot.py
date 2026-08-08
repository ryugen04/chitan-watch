import unittest

from chitan_watch.snapshot import SnapshotFetchError, build_snapshot, compute_sha256


class SnapshotTest(unittest.TestCase):
    def test_compute_sha256(self):
        self.assertEqual("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", compute_sha256(b"hello"))

    def test_build_snapshot_metadata(self):
        snapshot = build_snapshot(
            artifact_id="art_fixture",
            source_url="https://www.ssk.or.jp/example.csv",
            http_status=200,
            headers={"Content-Type": "text/csv", "Content-Length": "5", "ETag": "abc", "Last-Modified": "Sat, 08 Aug 2026 00:00:00 GMT"},
            content=b"hello",
            retrieved_at="2026-08-08T00:00:00+00:00",
        )
        self.assertEqual("art_fixture", snapshot.artifact_id)
        self.assertEqual(200, snapshot.http_status)
        self.assertEqual("text/csv", snapshot.content_type)
        self.assertEqual(5, snapshot.content_length)
        self.assertEqual("abc", snapshot.etag)
        self.assertEqual("Sat, 08 Aug 2026 00:00:00 GMT", snapshot.last_modified)

    def test_http_failure_is_not_a_snapshot(self):
        with self.assertRaises(SnapshotFetchError):
            build_snapshot(
                artifact_id="art_fixture",
                source_url="https://www.ssk.or.jp/missing.csv",
                http_status=500,
                headers={},
                content=b"",
            )


if __name__ == "__main__":
    unittest.main()
