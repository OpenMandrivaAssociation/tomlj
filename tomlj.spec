Name:		tomlj
Version:	2.2.0
Release:	2
Summary:	Java parser for TOML
Group:		Development/Java
License:	ASL 2.0
URL:		https://github.com/tomlj/tomlj
Source0:	https://github.com/tomlj/tomlj/archive/refs/tags/%{version}.tar.gz#/tomlj-%{version}.tar.gz
# Gradle 9.9.1 strictly pins 1.0.0. The wrapper jar is not in this archive.
Source1:	https://github.com/tomlj/tomlj/archive/refs/tags/1.0.0.tar.gz#/tomlj-1.0.0.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	antlr4-tool
BuildRequires:	antlr4
BuildRequires:	python
BuildRequires:	sysjar

# build-classpath belongs to javapackages-tools, which is not installed
# in this build root. antlr4 installs this jar.
%global antlr_jar %{_javadir}/antlr4-runtime.jar

%description
TomlJ parses and writes TOML. Gradle 8.11.1 reads version catalogs
through Toml.parse, getTable, getString, getArray, getBoolean and
TomlArray.toList. This jar links the system ANTLR 4 runtime. The
upstream org.tomlj:tomlj jar bundles that runtime under another name.
%{version} stays the default jar. Gradle 9.9.1 strictly pins 1.0.0,
so that jar is installed beside it.

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
%setup -q -T -D -a 1 -n tomlj-%{version}
find tomlj-1.0.0 \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -delete
# 1.0.0 annotates with jsr305. Gradle reads the parser, not those annotations.
python - <<'PY'
import re
from pathlib import Path
root = Path("tomlj-1.0.0/src/main/java")
for path in root.rglob("*.java"):
    text = path.read_text()
    new = text
    new = new.replace("import javax.annotation.Nullable;\n", "")
    new = new.replace("import javax.annotation.ParametersAreNonnullByDefault;\n", "")
    new = new.replace("import org.checkerframework.checker.nullness.qual.Nullable;\n", "")
    new = re.sub(r"@Nullable\b\s*", "", new)
    new = re.sub(r"@ParametersAreNonnullByDefault\b\s*", "", new)
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
	-cp %{antlr_jar} \
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
mkdir -p tomlj100/generated tomlj100/classes
gen100=$(pwd)/tomlj100/generated
(
	cd tomlj-1.0.0/src/main/antlr/org/tomlj/internal
	antlr4 -visitor -long-messages -o "$gen100" TomlLexer.g4 TomlParser.g4
)
find tomlj-1.0.0/src/main/java tomlj100/generated -name '*.java' > tomlj100/sources.list
test -s tomlj100/sources.list
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{antlr_jar} \
	-d tomlj100/classes @tomlj100/sources.list
jar cf tomlj100/tomlj.jar -C tomlj100/classes .
cat > tomlj100/tomlj.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.tomlj</groupId>
  <artifactId>tomlj</artifactId>
  <version>1.0.0</version>
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
        System.out.println("tomlj220_ok " + result.getTable("metadata").getString("format.version"));
    }
}
END
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{name}.jar:%{antlr_jar} \
	-d check check/Smoke.java
java -cp check:%{name}.jar:%{antlr_jar} Smoke > check220.log
cat check220.log
grep -F -q 'tomlj220_ok 1.1' check220.log
mkdir -p check100
cat > check100/Smoke.java << 'EOF'
import org.tomlj.Toml;
import org.tomlj.TomlParseResult;
import org.tomlj.TomlTable;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

public class Smoke {
    public static void main(String[] args) throws Exception {
        String toml = "[metadata]\nformat.version = \"1.1\"\n"
            + "[libraries]\nfoo = \"a:b:1\"\n";
        TomlParseResult result = Toml.parse(new ByteArrayInputStream(toml.getBytes(StandardCharsets.UTF_8)));
        if (result.hasErrors()) {
            throw new IllegalStateException(result.errors().get(0).getMessage());
        }
        String version = result.getTable("metadata").getString("format.version");
        if (!"1.1".equals(version)) {
            throw new IllegalStateException(version);
        }
        TomlTable libs = result.getTable("libraries");
        if (!"a:b:1".equals(String.valueOf(libs.get("foo")))) {
            throw new IllegalStateException("foo " + libs.get("foo"));
        }
        System.out.println(args[0] + " " + version);
    }
}
EOF
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp tomlj100/tomlj.jar:%{antlr_jar} \
	-d check100 check100/Smoke.java
java -cp check100:tomlj100/tomlj.jar:%{antlr_jar} Smoke tomlj100_ok > check100.log
cat check100.log
grep -F -q 'tomlj100_ok 1.1' check100.log

%install
sysjar install --buildroot %{buildroot} \
	--artifact tomlj100/tomlj.pom:tomlj100/tomlj.jar \
	--file-name tomlj-1.0.0 \
	--filelist .mfiles100
# %{version} owns tomlj.sysjar. 1.0.0 keeps a second index file.
/bin/mv %{buildroot}/usr/share/sysjar/index/org.tomlj/tomlj.sysjar \
	%{buildroot}/usr/share/sysjar/index/org.tomlj/tomlj-1.0.0.sysjar
sed -i 's|/usr/share/sysjar/index/org.tomlj/tomlj\.sysjar|/usr/share/sysjar/index/org.tomlj/tomlj-1.0.0.sysjar|' .mfiles100
sysjar install --buildroot %{buildroot} \
	--artifact %{name}.pom:%{name}.jar \
	--file-name %{name} \
	--filelist .mfiles
while IFS= read -r line; do
	grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
done < .mfiles100

%files -f .mfiles
%doc LICENSE README.md
