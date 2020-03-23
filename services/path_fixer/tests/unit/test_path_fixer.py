from tests.base import BaseTestCase

from services.path_fixer import PathFixer, invert_pattern


class TestPathFixerHelpers(BaseTestCase):
    def test_invert_pattern(self):
        assert invert_pattern("aaaa") == "!aaaa"
        assert invert_pattern("!aaaa") == "aaaa"


class TestPathFixer(BaseTestCase):
    def test_path_fixer_empty(self):
        pf = PathFixer([], [], [])
        assert pf("simple/path/to/something.py") == "simple/path/to/something.py"
        assert pf("") is None
        assert pf("bower_components/sample.js") == ""

    def test_path_fixer_with_toc(self):
        pf = PathFixer([], [], ",".join(["file_1.py", "folder/file_2.py"]))
        assert pf("fafafa/file_2.py") is None
        assert pf("folder/file_2.py") == "folder/file_2.py"
        assert pf("file_1.py") == "file_1.py"
        assert pf("bad_path.py") is None
        assert pf("") is None

    def test_path_fixer_one_exclude_path_pattern(self):
        pf = PathFixer([], ["!simple/path"], [])
        assert pf("notsimple/path/to/something.py") == "notsimple/path/to/something.py"
        assert (
            pf("simple/notapath/to/something.py") == "simple/notapath/to/something.py"
        )
        assert pf("simple/path/to/something.py") is None

    def test_path_fixer_one_custom_pathfix(self):
        pf = PathFixer(["before/::after/"], [], [])
        assert pf("before/path/to/something.py") == "after/path/to/something.py"
        assert pf("after/path/to/something.py") == "after/path/to/something.py"
        assert (
            pf("after/before/path/to/something.py")
            == "after/before/path/to/something.py"
        )
        assert (
            pf("simple/notapath/to/something.py") == "simple/notapath/to/something.py"
        )

    def test_init_from_user_yaml(self):
        commit_yaml = {
            "fixes": [r"(?s:before/tests\-[^\/]+)::after/"],
            "ignore": ["complex/path"],
            "flags": {
                "flagone": {"paths": ["!simple/notapath.*"]},
                "flagtwo": {"paths": ["af"]},
            },
        }
        toc = []
        flags = ["flagone"]
        pf = PathFixer.init_from_user_yaml(commit_yaml, toc, flags)
        assert pf("notsimple/path/to/something.py") == "notsimple/path/to/something.py"
        assert pf("complex/path/to/something.py") is None
        assert pf("before/tests-apples/test.js") == "after/test.js"
        assert pf("after/path/to/something.py") == "after/path/to/something.py"
        assert (
            pf("after/before/path/to/something.py")
            == "after/before/path/to/something.py"
        )
        assert pf("simple/notapath/to/something.py") is None


class TestBasePathAwarePathFixer(object):
    def test_basepath_uses_main_result_when_disagreement(self):
        commit_yaml = {
            "fixes": [r"(?s:home/thiago)::root/"],
            "ignore": ["complex/path"],
        }
        toc = "path.c,another/path.py,root/another/path.py"
        flags = []
        pf = PathFixer.init_from_user_yaml(commit_yaml, toc, flags)
        base_path = "/home/thiago/testing"
        base_aware_pf = pf.get_relative_path_aware_pathfixer(base_path)
        assert base_aware_pf("sample/path.c") == "path.c"
        assert base_aware_pf("another/path.py") == "another/path.py"
        assert base_aware_pf("/another/path.py") == "another/path.py"
        assert len(base_aware_pf.unexpected_results) == 1
        assert base_aware_pf.log_abnormalities()
        assert base_aware_pf.unexpected_results.pop() == (
            "another/path.py",
            "another/path.py",
            "root/another/path.py",
        )
        assert not base_aware_pf.log_abnormalities()