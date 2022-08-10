from io import BytesIO

from services.report.parser import RawReportParser

simple_content = b"""./codecov.yaml
Makefile
awesome/__init__.py
awesome/code_fib.py
dev.sh
tests/__init__.py
tests/test_number_two.py
tests/test_sample.py
unit.coverage.xml
<<<<<< network
# path=flagtwo.coverage.xml
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0" branches-valid="0" complexity="0" line-rate="0.6" lines-covered="30" lines-valid="50" timestamp="1600652028856" version="4.5.4">
    <!-- Generated by coverage.py: https://coverage.readthedocs.io -->
    <!-- Based on https://raw.githubusercontent.com/cobertura/web/master/htdocs/xml/coverage-04.dtd -->
    <sources>
        <source>/Users/thiagorramos/Projects/clientenv/example-python</source>
    </sources>
    <packages>
        <package branch-rate="0" complexity="0" line-rate="0.68" name="awesome">
            <classes>
                <class branch-rate="0" complexity="0" filename="awesome/__init__.py" line-rate="0.6471" name="__init__.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                    </lines>
                </class>
                <class branch-rate="0" complexity="0" filename="awesome/code_fib.py" line-rate="0.75" name="code_fib.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                    </lines>
                </class>
            </classes>
        </package>
        <package branch-rate="0" complexity="0" line-rate="0.52" name="tests">
            <classes>
                <class branch-rate="0" complexity="0" filename="tests/__init__.py" line-rate="1" name="__init__.py">
                    <methods/>
                    <lines/>
                </class>
                <class branch-rate="0" complexity="0" filename="tests/test_number_two.py" line-rate="0" name="test_number_two.py">
                    <methods/>
                    <lines>
                        <line hits="0" number="1"/>
                    </lines>
                </class>
                <class branch-rate="0" complexity="0" filename="tests/test_sample.py" line-rate="1" name="test_sample.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
<<<<<< EOF"""


simple_no_toc = b"""
# path=flagtwo.coverage.xml
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0" branches-valid="0" complexity="0" line-rate="0.6" lines-covered="30" lines-valid="50" timestamp="1600652028856" version="4.5.4">
    <!-- Generated by coverage.py: https://coverage.readthedocs.io -->
    <!-- Based on https://raw.githubusercontent.com/cobertura/web/master/htdocs/xml/coverage-04.dtd -->
    <sources>
        <source>/Users/thiagorramos/Projects/clientenv/example-python</source>
    </sources>
    <packages>
        <package branch-rate="0" complexity="0" line-rate="0.68" name="awesome">
            <classes>
                <class branch-rate="0" complexity="0" filename="awesome/__init__.py" line-rate="0.6471" name="__init__.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                    </lines>
                </class>
                <class branch-rate="0" complexity="0" filename="awesome/code_fib.py" line-rate="0.75" name="code_fib.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                    </lines>
                </class>
            </classes>
        </package>
        <package branch-rate="0" complexity="0" line-rate="0.52" name="tests">
            <classes>
                <class branch-rate="0" complexity="0" filename="tests/__init__.py" line-rate="1" name="__init__.py">
                    <methods/>
                    <lines/>
                </class>
                <class branch-rate="0" complexity="0" filename="tests/test_number_two.py" line-rate="0" name="test_number_two.py">
                    <methods/>
                    <lines>
                        <line hits="0" number="1"/>
                    </lines>
                </class>
                <class branch-rate="0" complexity="0" filename="tests/test_sample.py" line-rate="1" name="test_sample.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
<<<<<< EOF"""

more_complex = b"""PRODUCTION_TOKEN=aaaaaaaa-e799-40d4-b89d-cea4b18f29a4
<<<<<< ENV
./codecov.yaml
Makefile
awesome/__init__.py
awesome/code_fib.py
dev.sh
tests/__init__.py
tests/test_number_two.py
tests/test_sample.py
unit.coverage.xml
<<<<<< network
# path=unit.coverage.xml
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0" branches-valid="0" complexity="0" line-rate="0.8636" lines-covered="38" lines-valid="44" timestamp="1581335242903" version="4.5.4">
    <!-- Generated by coverage.py: https://coverage.readthedocs.io -->
    <!-- Based on https://raw.githubusercontent.com/cobertura/web/master/htdocs/xml/coverage-04.dtd -->
    <sources>
        <source>/Users/thiagorramos/Projects/clientenv/example-python</source>
    </sources>
    <packages>
        <package branch-rate="0" complexity="0" line-rate="1" name="tests">
            <classes>
                <class branch-rate="0" complexity="0" filename="tests/__init__.py" line-rate="1" name="__init__.py">
                    <methods/>
                    <lines/>
                </class>
                <class branch-rate="0" complexity="0" filename="tests/test_sample.py" line-rate="1" name="test_sample.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                        <line hits="0" number="17"/>
                        <line hits="1" number="18"/>
                        <line hits="1" number="21"/>
                        <line hits="1" number="22"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
<<<<<< EOF
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0" branches-valid="0" complexity="0" line-rate="0.56" lines-covered="28" lines-valid="50" timestamp="1600652026658" version="4.5.4">
    <!-- Generated by coverage.py: https://coverage.readthedocs.io -->
    <!-- Based on https://raw.githubusercontent.com/cobertura/web/master/htdocs/xml/coverage-04.dtd -->
    <sources>
        <source>/Users/thiagorramos/Projects/clientenv/example-python</source>
    </sources>
    <packages>
        <package branch-rate="0" complexity="0" line-rate="0.64" name="awesome">
            <classes>
                <class branch-rate="0" complexity="0" filename="awesome/__init__.py" line-rate="0.5882" name="__init__.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                    </lines>
                </class>
                <class branch-rate="0" complexity="0" filename="awesome/code_fib.py" line-rate="0.75" name="code_fib.py">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                        <line hits="0" number="10"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
<<<<<< EOF"""

more_complex_with_line_end = b"""PRODUCTION_TOKEN=aaaaaaaa-e799-40d4-b89d-cea4b18f29a4
<<<<<< ENV
./codecov.yaml
Makefile
awesome/__init__.py
awesome/code_fib.py
dev.sh
tests/__init__.py
tests/test_number_two.py
tests/test_sample.py
unit.coverage.xml
<<<<<< network
# path=unit.coverage.xml
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0">
    <packages>
    </packages>
</coverage>
<<<<<< EOF
# path=profile.cov
mode: count
github.com/path/ckey/key.go:43.38,47.2 1 1
github.com/path/ckey/key.go:51.82,58.45 2 12
github.com/path/ckey/key.go:64.2,66.33 3 12
github.com/path/ckey/key.go:70.2,72.41 2 12
github.com/path/ckey/key.go:58.45,60.3 1 12
github.com/path/ckey/key.go:60.8,62.3 1 0
<<<<<< EOF
"""

line_end_no_line_break = b"""PRODUCTION_TOKEN=aaaaaaaa-e799-40d4-b89d-cea4b18f29a4
<<<<<< ENV
./codecov.yaml
Makefile
awesome/__init__.py
awesome/code_fib.py
dev.sh
tests/__init__.py
tests/test_number_two.py
tests/test_sample.py
unit.coverage.xml
<<<<<< network
# path=unit.coverage.xml
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0">
    <packages>
    </packages>
</coverage><<<<<< EOF
# path=profile.cov
mode: count
github.com/path/ckey/key.go:43.38,47.2 1 1
github.com/path/ckey/key.go:51.82,58.45 2 12
github.com/path/ckey/key.go:64.2,66.33 3 12
github.com/path/ckey/key.go:70.2,72.41 2 12
github.com/path/ckey/key.go:58.45,60.3 1 12
github.com/path/ckey/key.go:60.8,62.3 1 0<<<<<< EOF
"""

cases_little_mor_ridiculous = b"""PRODUCTION_TOKEN=aaaaaaaa-e799-40d4-b89d-cea4b18f29a4
<<<<<< ENV
./codecov.yaml
Makefile
awesome/__init__.py
awesome/code_fib.py
dev.sh
tests/__init__.py
tests/test_number_two.py
tests/test_sample.py
unit.coverage.xml
<<<<<< network
# path=unit.coverage.xml
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0">
</coverage><<<<<<< EOF# path=profile.cov
mode: count
github.com/path/ckey/key.go:43.38,47.2 1 1
github.com/path/ckey/key.go:51.82,58.45 2 12
github.com/path/ckey/key.go:64.2,66.33 3 12
github.com/path/ckey/key.go:70.2,72.41 2 12
github.com/path/ckey/key.go:58.45,60.3 1 12
github.com/path/ckey/key.go:60.8,62.3 1 0\r










<<<<<< EOF
"""

cases_no_eof_end = b"""PRODUCTION_TOKEN=aaaaaaaa-e799-40d4-b89d-cea4b18f29a4
<<<<<< ENV
./codecov.yaml
Makefile
awesome/__init__.py
awesome/code_fib.py
dev.sh
tests/__init__.py
tests/test_number_two.py
tests/test_sample.py
unit.coverage.xml
<<<<<< network
# path=unit.coverage.xml
<?xml version="1.0" ?>
<coverage branch-rate="0" branches-covered="0">
</coverage><<<<<<< EOF# path=profile.cov
mode: count
github.com/path/ckey/key.go:43.38,47.2 1 1"""

cases_emptylines_betweenpath_and_content = b"""p2/redis/b_test.go
p1/driver.go
p1/driver_test.go
p1/options.go
p2/a.go
p2/a_test.go
<<<<<< network
# path=coverage.txt

mode: count
mode: count
github.com/mypath/bugsbunny.go:10.33,13.20 1 3
github.com/mypath/bugsbunny.go:19.2,20.36 2 2
github.com/mypath/bugsbunny.go:26.2,26.22 1 2
github.com/mypath/bugsbunny.go:31.2,38.16 3 2
github.com/mypath/bugsbunny.go:41.2,43.12 2 2
github.com/mypath/bugsbunny.go:13.20,16.3 2 1
github.com/mypath/bugsbunny.go:20.36,22.17 2 1"""


class TestParser(object):
    def test_parser_with_toc(self):
        res = RawReportParser().parse_raw_report_from_bytes(simple_content)
        assert res.has_toc()
        assert not res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 1

    def test_parser_no_toc(self):
        res = RawReportParser().parse_raw_report_from_bytes(simple_no_toc)
        assert not res.has_toc()
        assert not res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 1

    def test_parser_more_complete(self):
        res = RawReportParser().parse_raw_report_from_bytes(more_complex)
        assert res.has_toc()
        assert res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 2
        assert res.uploaded_files[0].filename == "unit.coverage.xml"
        assert res.uploaded_files[0].contents.startswith(b'<?xml version="1.0" ?>')
        assert res.uploaded_files[0].contents.endswith(b"</coverage>")
        assert res.uploaded_files[1].filename is None
        assert res.uploaded_files[1].contents.startswith(b'<?xml version="1.0" ?>')
        assert res.uploaded_files[1].contents.endswith(b"</coverage>")

    def test_parser_more_complete_with_line_end(self):
        res = RawReportParser().parse_raw_report_from_bytes(more_complex_with_line_end)
        assert res.has_toc()
        assert res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 2
        assert res.uploaded_files[0].filename == "unit.coverage.xml"
        assert (
            res.uploaded_files[0].contents
            == b'<?xml version="1.0" ?>\n<coverage branch-rate="0" branches-covered="0">\n    <packages>\n    </packages>\n</coverage>'
        )
        assert res.uploaded_files[1].filename == "profile.cov"
        expected_second_file = b"\n".join(
            [
                b"mode: count",
                b"github.com/path/ckey/key.go:43.38,47.2 1 1",
                b"github.com/path/ckey/key.go:51.82,58.45 2 12",
                b"github.com/path/ckey/key.go:64.2,66.33 3 12",
                b"github.com/path/ckey/key.go:70.2,72.41 2 12",
                b"github.com/path/ckey/key.go:58.45,60.3 1 12",
                b"github.com/path/ckey/key.go:60.8,62.3 1 0",
            ]
        )
        assert res.uploaded_files[1].contents == expected_second_file

    def test_line_end_no_line_break(self):
        res = RawReportParser().parse_raw_report_from_bytes(line_end_no_line_break)
        assert res.has_toc()
        assert res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 2
        assert res.uploaded_files[0].filename == "unit.coverage.xml"
        assert (
            res.uploaded_files[0].contents
            == b'<?xml version="1.0" ?>\n<coverage branch-rate="0" branches-covered="0">\n    <packages>\n    </packages>\n</coverage>'
        )
        assert res.uploaded_files[1].filename == "profile.cov"
        expected_second_file = b"\n".join(
            [
                b"mode: count",
                b"github.com/path/ckey/key.go:43.38,47.2 1 1",
                b"github.com/path/ckey/key.go:51.82,58.45 2 12",
                b"github.com/path/ckey/key.go:64.2,66.33 3 12",
                b"github.com/path/ckey/key.go:70.2,72.41 2 12",
                b"github.com/path/ckey/key.go:58.45,60.3 1 12",
                b"github.com/path/ckey/key.go:60.8,62.3 1 0",
            ]
        )
        assert res.uploaded_files[1].contents == expected_second_file

    def test_cases_little_mor_ridiculous(self):
        res = RawReportParser().parse_raw_report_from_bytes(cases_little_mor_ridiculous)
        assert res.has_toc()
        assert res.toc.getvalue() == b"\n".join(
            [
                b"./codecov.yaml",
                b"Makefile",
                b"awesome/__init__.py",
                b"awesome/code_fib.py",
                b"dev.sh",
                b"tests/__init__.py",
                b"tests/test_number_two.py",
                b"tests/test_sample.py",
                b"unit.coverage.xml",
            ]
        )
        assert res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 2
        assert res.uploaded_files[0].filename == "unit.coverage.xml"
        assert (
            res.uploaded_files[0].contents
            == b'<?xml version="1.0" ?>\n<coverage branch-rate="0" branches-covered="0">\n</coverage><'
        )
        assert res.uploaded_files[1].filename == "profile.cov"
        expected_second_file = b"\n".join(
            [
                b"mode: count",
                b"github.com/path/ckey/key.go:43.38,47.2 1 1",
                b"github.com/path/ckey/key.go:51.82,58.45 2 12",
                b"github.com/path/ckey/key.go:64.2,66.33 3 12",
                b"github.com/path/ckey/key.go:70.2,72.41 2 12",
                b"github.com/path/ckey/key.go:58.45,60.3 1 12",
                b"github.com/path/ckey/key.go:60.8,62.3 1 0",
            ]
        )
        assert res.uploaded_files[1].contents == expected_second_file

    def test_cases_no_eof_end(self):
        res = RawReportParser().parse_raw_report_from_bytes(cases_no_eof_end)
        assert res.has_toc()
        assert res.toc.getvalue() == b"\n".join(
            [
                b"./codecov.yaml",
                b"Makefile",
                b"awesome/__init__.py",
                b"awesome/code_fib.py",
                b"dev.sh",
                b"tests/__init__.py",
                b"tests/test_number_two.py",
                b"tests/test_sample.py",
                b"unit.coverage.xml",
            ]
        )
        assert res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 2
        assert res.uploaded_files[0].filename == "unit.coverage.xml"
        assert (
            res.uploaded_files[0].contents
            == b'<?xml version="1.0" ?>\n<coverage branch-rate="0" branches-covered="0">\n</coverage><'
        )
        assert res.uploaded_files[1].filename == "profile.cov"
        expected_second_file = b"\n".join(
            [b"mode: count", b"github.com/path/ckey/key.go:43.38,47.2 1 1"]
        )
        assert res.uploaded_files[1].contents == expected_second_file

    def test_cases_emptylines_betweenpath_and_content(self):
        res = RawReportParser().parse_raw_report_from_bytes(
            cases_emptylines_betweenpath_and_content
        )
        assert res.has_toc()
        assert res.toc.getvalue() == b"\n".join(
            [
                b"p2/redis/b_test.go",
                b"p1/driver.go",
                b"p1/driver_test.go",
                b"p1/options.go",
                b"p2/a.go",
                b"p2/a_test.go",
            ]
        )
        assert not res.has_env()
        assert not res.has_path_fixes()
        assert len(res.uploaded_files) == 1
        assert res.uploaded_files[0].filename == "coverage.txt"
        assert (
            res.uploaded_files[0].contents
            == b"""mode: count
mode: count
github.com/mypath/bugsbunny.go:10.33,13.20 1 3
github.com/mypath/bugsbunny.go:19.2,20.36 2 2
github.com/mypath/bugsbunny.go:26.2,26.22 1 2
github.com/mypath/bugsbunny.go:31.2,38.16 3 2
github.com/mypath/bugsbunny.go:41.2,43.12 2 2
github.com/mypath/bugsbunny.go:13.20,16.3 2 1
github.com/mypath/bugsbunny.go:20.36,22.17 2 1"""
        )

    def test_cases_compatibility_mode(self):
        res = RawReportParser().parse_raw_report_from_bytes(
            b"==FROMNOWONIGNOREDBYCODECOV==>>>".join([simple_content, more_complex])
        )
        would_be_simple_content_res = RawReportParser().parse_raw_report_from_bytes(
            simple_content
        )
        assert res.has_toc()
        assert would_be_simple_content_res.has_toc()
        assert res.toc.getvalue() == would_be_simple_content_res.toc.getvalue()
        assert not res.has_env()
        assert not would_be_simple_content_res.has_env()
        assert not res.has_path_fixes()
        assert not would_be_simple_content_res.has_path_fixes()
        assert len(res.uploaded_files) == len(
            would_be_simple_content_res.uploaded_files
        )
        assert (
            res.uploaded_files[0].filename
            == would_be_simple_content_res.uploaded_files[0].filename
        )
        assert (
            res.uploaded_files[0].contents
            == would_be_simple_content_res.uploaded_files[0].contents
        )

    def test_cases_compatibility_mode_failed_case(self):
        res = RawReportParser().parse_raw_report_from_bytes(
            b"==FROMNOWONIGNOREDBYCODECOV==>>>".join(
                [simple_content, b"somemeaninglessstuff"]
            )
        )
        would_be_simple_content_res = RawReportParser().parse_raw_report_from_bytes(
            simple_content
        )
        assert res.has_toc()
        assert would_be_simple_content_res.has_toc()
        assert res.toc.getvalue() == would_be_simple_content_res.toc.getvalue()
        assert not res.has_env()
        assert not would_be_simple_content_res.has_env()
        assert not res.has_path_fixes()
        assert not would_be_simple_content_res.has_path_fixes()
        assert len(res.uploaded_files) == len(
            would_be_simple_content_res.uploaded_files
        )
        assert (
            res.uploaded_files[0].filename
            == would_be_simple_content_res.uploaded_files[0].filename
        )
        assert (
            res.uploaded_files[0].contents
            == would_be_simple_content_res.uploaded_files[0].contents
        )
