Name:		tomlj
Version:	2.2.0
Release:	1
Summary:	Java parser for TOML
Group:		Development/Java
License:	ASL 2.0
URL:		https://github.com/tomlj/tomlj
Source0:	https://github.com/tomlj/tomlj/archive/refs/tags/%{version}.tar.gz#/tomlj-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	antlr4-tool
BuildRequires:	antlr4
BuildRequires:	python
BuildRequires:	sysjar

%description
TomlJ parses and writes TOML. Gradle 8.11.1 reads version catalogs
through Toml.parse, getTable, getString, getArray, getBoolean and
TomlArray.toList. This jar links the system ANTLR 4 runtime. The
upstream org.tomlj:tomlj jar bundles that runtime under another name.

%prep
%autosetup -n tomlj-%{version}
# @Nullable comes from checker-qual, which is not packaged. The
# annotations do not change the parser. The upstream shaded jar
# leaves checker-qual out as well.
python - <<'PY'
import re
from pathlib import Path

for path in Path("src/main/java").rglob("*.java"):
    text = path.read_text()
    new = text.replace("import org.checkerframework.checker.nullness.qual.Nullable;\n", "")
    new = re.sub(r"@Nullable\b\s*", "", new)
    if new != text:
        path.write_text(new)
PY

%build
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH=$JAVA_HOME/bin:$PATH
mkdir -p generated
gen=$(pwd)/generated
(
	cd src/main/antlr/org/tomlj/internal
	antlr4 -visitor -long-messages -o "$gen" TomlLexer.g4 TomlParser.g4
)
find src/main/java generated -name '*.java' > sources.list
mkdir -p classes
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp "$(build-classpath antlr4-runtime)" \
	-d classes @sources.list
jar cf %{name}.jar -C classes .
cat > %{name}.pom <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.tomlj</groupId>
  <artifactId>tomlj</artifactId>
  <version>%{version}</version>
  <name>tomlj</name>
  <description>Parser and serializer for TOML. Links the system ANTLR 4 runtime.</description>
  <url>https://github.com/tomlj/tomlj</url>
  <licenses>
    <license>
      <name>The Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.antlr</groupId>
      <artifactId>antlr4-runtime</artifactId>
      <version>4.13.2</version>
    </dependency>
  </dependencies>
</project>
EOF

%check
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH=$JAVA_HOME/bin:$PATH
mkdir -p check
cat > check/Smoke.java <<'END'
import org.tomlj.Toml;
import org.tomlj.TomlArray;
import org.tomlj.TomlParseError;
import org.tomlj.TomlParseResult;
import org.tomlj.TomlTable;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

public class Smoke {
    public static void main(String[] args) throws Exception {
        String toml = "[metadata]\nformat.version = \"1.1\"\n"
            + "[versions]\nok = { require = \"1.0\", reject = [\"1.0.1\"], rejectAll = false }\n"
            + "[libraries]\nfoo = \"a:b:1\"\nbar = { module = \"g:n\", version.ref = \"ok\" }\n";
        TomlParseResult result = Toml.parse(new ByteArrayInputStream(toml.getBytes(StandardCharsets.UTF_8)));
        if (result.hasErrors()) {
            throw new IllegalStateException(result.errors().get(0).getMessage());
        }
        if (!result.keySet().contains("libraries")) {
            throw new IllegalStateException("libraries");
        }
        if (!"1.1".equals(result.getTable("metadata").getString("format.version"))) {
            throw new IllegalStateException("format");
        }
        TomlTable libs = result.getTable("libraries");
        if (!"a:b:1".equals(libs.get("foo"))) {
            throw new IllegalStateException("foo");
        }
        if (!"ok".equals(((TomlTable) libs.get("bar")).getString("version.ref"))) {
            throw new IllegalStateException("ref");
        }
        TomlArray reject = ((TomlTable) result.getTable("versions").get("ok")).getArray("reject");
        if (reject.toList().size() != 1) {
            throw new IllegalStateException("reject");
        }
        TomlParseResult bad = Toml.parse(new ByteArrayInputStream("[\n".getBytes(StandardCharsets.UTF_8)));
        if (!bad.hasErrors()) {
            throw new IllegalStateException("errors");
        }
        TomlParseError error = bad.errors().get(0);
        if (error.position().line() < 1 || error.position().column() < 1) {
            throw new IllegalStateException("position");
        }
    }
}
END
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{name}.jar:"$(build-classpath antlr4-runtime)" \
	-d check check/Smoke.java
java -cp check:%{name}.jar:"$(build-classpath antlr4-runtime)" Smoke

%install
sysjar install --buildroot %{buildroot} \
	--artifact %{name}.pom:%{name}.jar \
	--file-name %{name} \
	--filelist .mfiles

%files -f .mfiles
%doc LICENSE README.md
