#!/usr/bin/env python3
"""Build independent QA editor and all-window instrumentation APKs without Gradle."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk', default=os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT'))
    p.add_argument('--jdk', default=os.environ.get('JAVA_HOME'))
    p.add_argument('--output', type=Path, default=Path('outputs/qa-editor'))
    args = p.parse_args()
    if not args.sdk or not args.jdk:
        p.error('Set ANDROID_HOME and JAVA_HOME, or pass --sdk and --jdk')
    sdk, jdk = Path(args.sdk), Path(args.jdk)
    tools, android = sdk/'build-tools/36.0.0', sdk/'platforms/android-36/android.jar'
    sources, out = Path(__file__).resolve().parent, args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    windows = os.name == 'nt'
    def tool(base, name, batch=False):
        return str(base/(name + ('.bat' if batch else '.exe') if windows else name))
    def run(*cmd):
        subprocess.run([str(x) for x in cmd], check=True, timeout=120,
                       env={**os.environ, 'JAVA_HOME': str(jdk)})
    key = out/'qa-only.keystore'
    if not key.exists():
        run(tool(jdk/'bin','keytool'),'-genkeypair','-keystore',key,'-storepass','android',
            '-keypass','android','-alias','qa','-keyalg','RSA','-keysize','2048',
            '-validity','3650','-dname','CN=Local QA Only')
    hashes = []
    for name in ('editor','automation'):
        source, build = sources/name, out/('build-'+name)
        classes, dex = build/'classes', build/'dex'
        classes.mkdir(parents=True,exist_ok=True)
        dex.mkdir(parents=True,exist_ok=True)
        run(tool(jdk/'bin','javac'), '-encoding','UTF-8','-source','8','-target','8',
            '-classpath',android,'-d',classes,*sorted(source.glob('*.java')))
        run(tool(jdk/'bin','jar'),'cf',build/'classes.jar','-C',classes,'.')
        run(tool(tools,'d8',True),'--lib',android,'--min-api','23','--output',dex,build/'classes.jar')
        run(tool(tools,'aapt2'),'link','-I',android,'--manifest',source/'AndroidManifest.xml','-o',build/'unsigned.apk')
        with zipfile.ZipFile(build/'unsigned.apk','a',compression=zipfile.ZIP_DEFLATED) as z:
            z.write(dex/'classes.dex','classes.dex')
        run(tool(tools,'zipalign'),'-f','4',build/'unsigned.apk',build/'aligned.apk')
        apk = out/('trime-qa-'+name+'.apk')
        run(tool(tools,'apksigner',True),'sign','--ks',key,'--ks-pass','pass:android',
            '--key-pass','pass:android','--ks-key-alias','qa','--out',apk,build/'aligned.apk')
        run(tool(tools,'apksigner',True),'verify','--verbose',apk)
        run(tool(tools,'aapt2'),'dump','badging',apk)
        hashes.append(hashlib.sha256(apk.read_bytes()).hexdigest()+'  '+apk.name+'\n')
        print(apk)
    (out/'sha256.txt').write_text(''.join(hashes))


if __name__ == '__main__':
    main()
