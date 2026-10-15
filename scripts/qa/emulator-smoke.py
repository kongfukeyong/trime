#!/usr/bin/env python3
"""Bounded, evidence-first smoke test for a fresh, disposable Android emulator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

PACKAGE = 'com.osfans.trime.debug'
EDITOR = 'local.trime.qa.editor'
IME = PACKAGE + '/com.osfans.trime.ime.core.TrimeInputMethodService'
CASES = ['install', 'launch', 'enable-ime', 'wanxiang-deployment', 'mode-bar',
         'auto-pinyin', 'auto-english', 'force-chinese', 'force-english']


def select_apk(path):
    files = [path] if path.is_file() else list(path.rglob('*.apk'))
    matches = []
    for file in files:
        with zipfile.ZipFile(file) as z:
            if 'lib/x86_64/librime_jni.so' in z.namelist():
                matches.append(file)
    if len(matches) != 1:
        raise RuntimeError(f'Expected exactly one x86_64 Trime APK, found {matches}')
    return matches[0]


def center(bounds):
    points = list(map(int, re.findall(r'\d+', bounds)))
    if len(points) != 4 or points[2] <= points[0] or points[3] <= points[1]:
        raise ValueError('Invalid UI bounds: '+bounds)
    return (points[0]+points[2])//2, (points[1]+points[3])//2


class Smoke:
    def __init__(self, args):
        self.args, self.out = args, args.output.resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.results = {case: {'status': 'NOT_RUN'} for case in CASES}
        self.base = [args.adb] + (['-s', args.serial] if args.serial else [])
        self.log_process = None
        self.log_handle = None

    def adb(self, *args, check=True, timeout=30, binary=False):
        result = subprocess.run(self.base+list(map(str,args)), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout)
        with (self.out/'commands.log').open('a',encoding='utf-8') as f:
            f.write(json.dumps(list(map(str,args)),ensure_ascii=False)+f' -> {result.returncode}\n')
            if not binary:
                f.write(result.stdout.decode('utf-8','replace')+result.stderr.decode('utf-8','replace'))
        if check and result.returncode:
            raise RuntimeError(f'adb {args} failed: {result.stderr.decode("utf-8", "replace")}')
        return result.stdout if binary else result.stdout.decode('utf-8','replace').strip()

    def nodes(self):
        self.adb('shell','uiautomator','dump','/sdcard/qa-window.xml',timeout=20)
        xml = self.adb('shell','cat','/sdcard/qa-window.xml')
        (self.out/'latest-ui.xml').write_text(xml,encoding='utf-8')
        return list(ET.fromstring(xml).iter('node'))

    def tap_node(self, node):
        self.adb('shell','input','tap',*center(node.get('bounds','')))
        time.sleep(.4)

    def button(self, labels):
        for node in self.nodes():
            text = node.get('text','').replace('✓','').strip().split(' · ')[0]
            if text in labels and node.get('class','').endswith('Button') and node.get('enabled') == 'true':
                self.tap_node(node)
                return
        raise RuntimeError('Button not found: '+repr(labels))

    def wait(self, predicate, seconds, description):
        deadline = time.monotonic()+seconds
        last = None
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except (RuntimeError, ET.ParseError, subprocess.TimeoutExpired) as error:
                last = str(error)
            time.sleep(2)
        raise RuntimeError(f'Timeout waiting for {description}; last={last}')

    def capture(self, label):
        try:
            (self.out/(label+'.png')).write_bytes(self.adb('exec-out','screencap','-p',binary=True))
            self.nodes()
            (self.out/(label+'.xml')).write_bytes((self.out/'latest-ui.xml').read_bytes())
        except Exception as error:
            (self.out/(label+'-capture-error.txt')).write_text(str(error))

    def mode(self, mode, language=None):
        labels = {'auto': ('Auto','自动'), 'chinese': ('Chinese','强制中文'), 'english': ('English','强制英文')}
        for node in self.nodes():
            text, desc = node.get('text',''), node.get('content-desc','')
            if '✓' in text and any(label in text for label in labels[mode]):
                if language is None or text.endswith(' · '+language) or desc.endswith(language):
                    return True
        return False

    def text(self):
        for node in self.nodes():
            if node.get('class') == 'android.widget.EditText' and node.get('package') == EDITOR:
                value = node.get('text','')
                return '' if value == 'Tap AUTO in the IME, then type nihao' else value
        raise RuntimeError('Editor field missing')

    def seed(self, label):
        self.button((label,))
        time.sleep(.5)

    def keys(self, text):
        # Physical key events traverse Trime.forwardKeyEvent/prepareLanguageForKey.
        # Never use `input text`, which can bypass IME processing.
        for char in text:
            self.adb('shell','input','keyevent','KEYCODE_'+char.upper())
            time.sleep(.15)

    def chinese_case(self, forced=False):
        self.seed('hello' if forced else 'Clear')
        self.button(('Chinese','强制中文') if forced else ('Auto','自动'))
        for char in 'nihao':
            self.keys(char)
            if not self.wait(lambda: self.mode('chinese' if forced else 'auto','中'),10,'Chinese mode during pinyin'):
                raise RuntimeError('Unexpected language')
        self.capture('force-chinese-composing' if forced else 'auto-pinyin-composing')
        # Space asks the real Rime engine to commit its first candidate.
        self.adb('shell','input','keyevent','KEYCODE_SPACE')
        prefix = 'hello' if forced else ''
        value = self.wait(lambda: (v if v.startswith(prefix) and re.search(r'[\u3400-\u9fff]',v[len(prefix):]) else False)
                          if (v := self.text()) else False,15,'Chinese candidate commit')
        return {'committed_text': value, 'input_path': 'physical-keyevent'}

    def english_case(self, forced=False):
        self.seed('你好' if forced else 'hello')
        self.button(('English','强制英文') if forced else ('Auto','自动'))
        self.keys('abc')
        expected = '你好abc' if forced else 'helloabc'
        self.wait(lambda: self.text() == expected,15,'exact English editor contents')
        self.wait(lambda: self.mode('english' if forced else 'auto','EN'),10,'English mode indicator')
        return {'committed_text': expected, 'input_path': 'physical-keyevent'}

    def case(self, name, action):
        started = time.monotonic()
        try:
            detail = action()
            self.results[name] = {'status':'PASS','detail':detail}
        except Exception as error:
            self.results[name] = {'status':'FAIL','error':str(error)}
            raise
        finally:
            self.results[name]['seconds'] = round(time.monotonic()-started,2)
            self.capture(name)
            self.save()

    def save(self):
        report = {'cases':self.results,'scope':'physical-keyevent IME path; soft-key touch gestures NOT TESTED',
                  'overall':'PASS' if all(v['status']=='PASS' for v in self.results.values()) else 'INCOMPLETE_OR_FAILED'}
        (self.out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

    def deployment(self):
        root = f'/sdcard/Android/data/{PACKAGE}/files'
        def ready():
            log = (self.out/'logcat.txt').read_text(encoding='utf-8',errors='replace')
            if 'DeployMessage(state=Success)' not in log:
                return False
            # Probe app-generated runtime output, never just packaged assets.
            for name in ('wanxiang.schema.yaml','wanxiang.prism.bin','wanxiang.table.bin','default.yaml'):
                result = self.adb('shell',f'test -s {root}/rime/build/{name} && echo READY',check=False)
                if result != 'READY':
                    return False
            default = self.adb('shell','cat',root+'/rime/build/default.yaml')
            schemas = re.findall(r'^\s*-\s*schema:\s*[\"\']?([\w-]+)', default, re.MULTILINE)
            if not schemas or schemas[0] != 'wanxiang':
                return False
            (self.out/'deployed-default.yaml').write_text(default,encoding='utf-8')
            return True
        self.wait(ready,self.args.deploy_timeout,'Wanxiang successful deployment and compiled dictionary')
        lock = json.loads((Path(__file__).resolve().parents[2]/'docs/wanxiang-resources.lock.json').read_text(encoding='utf-8'))
        model = next(item for item in lock['downloads'] if item['role'] == 'model')
        digest = self.adb('shell','sha256sum',root+'/rime/'+model['file'],timeout=120)
        if not digest.startswith(model['sha256']+' '):
            raise RuntimeError('Deployed Wanxiang model SHA-256 does not match lock: '+digest)
        (self.out/'deployed-model-sha256.txt').write_text(digest+'\n')
        for name in ('wanxiang.schema.yaml','default.yaml'):
            self.adb('pull',root+'/rime/build/'+name,self.out/('deployed-'+name))
        listing = self.adb('shell','ls','-lR',root,timeout=40)
        (self.out/'runtime-files.txt').write_text(listing,encoding='utf-8')
        return {'success_callback':True,'compiled_schema_prism_table':True,'default_schema':'wanxiang','model_sha256':model['sha256']}

    def run(self):
        self.save()
        try:
            self.adb('wait-for-device',timeout=120)
            if self.adb('shell','getprop','ro.kernel.qemu') != '1':
                raise RuntimeError('This script requires a disposable emulator')
            if self.adb('shell','pm','path',PACKAGE,check=False).startswith('package:'):
                raise RuntimeError('Product already installed: fresh emulator required for deployment proof')
            apk = select_apk(self.args.apk)
            (self.out/'apk-sha256.txt').write_text(hashlib.sha256(apk.read_bytes()).hexdigest()+'  '+str(apk)+'\n')
            self.adb('logcat','-c')
            self.log_handle = (self.out/'logcat.txt').open('wb')
            self.log_process = subprocess.Popen(self.base+['logcat','-v','threadtime'],stdout=self.log_handle,stderr=subprocess.STDOUT)
            self.case('install',lambda: self.adb('install',str(apk),timeout=180))
            self.adb('shell','pm','grant',PACKAGE,'android.permission.POST_NOTIFICATIONS',check=False)
            self.adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
            def enable():
                self.adb('shell','ime','enable',IME)
                self.adb('shell','ime','set',IME)
                selected = self.adb('shell','settings','get','secure','default_input_method')
                if selected != IME:
                    raise RuntimeError('Wrong default IME: '+selected)
                return selected
            self.case('enable-ime',enable)
            def launch():
                result = self.adb('shell','am','start','-W','-n',PACKAGE+'/com.osfans.trime.ui.main.MainActivity',timeout=60)
                if 'Error:' in result:
                    raise RuntimeError(result)
                self.wait(lambda: self.adb('shell','pidof',PACKAGE,check=False),30,'Trime process')
                return result
            self.case('launch',launch)
            self.adb('install','-r',self.args.editor,timeout=60)
            self.adb('shell','am','start','-W','-n',EDITOR+'/.MainActivity')
            self.case('wanxiang-deployment',self.deployment)
            def bar():
                def visible():
                    texts = [n.get('text','').replace('✓','').strip().split(' · ')[0] for n in self.nodes()]
                    return all(any(label in texts for label in group) for group in [('Auto','自动'),('Chinese','强制中文'),('English','强制英文')])
                self.wait(visible,45,'all three language mode buttons')
                return {'three_buttons':True}
            self.case('mode-bar',bar)
            for name, action in [('auto-pinyin',lambda:self.chinese_case()),('auto-english',lambda:self.english_case()),
                                 ('force-chinese',lambda:self.chinese_case(True)),('force-english',lambda:self.english_case(True))]:
                try:
                    self.case(name,action)
                except Exception:
                    # Isolated cases reset content/mode. Continue collecting failures.
                    pass
        except Exception:
            (self.out/'fatal-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        finally:
            self.capture('final')
            for name, cmd in [('input-method',['shell','dumpsys','input_method']),('activities',['shell','dumpsys','activity','activities']),
                              ('package',['shell','dumpsys','package',PACKAGE]),('getprop',['shell','getprop']),('crashes',['logcat','-b','crash','-d'])]:
                try:
                    (self.out/(name+'.txt')).write_text(self.adb(*cmd,check=False),encoding='utf-8')
                except Exception:
                    pass
            if self.log_process:
                self.log_process.terminate()
                try:
                    self.log_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.log_process.kill()
                self.log_handle.close()
            self.save()
        return 0 if all(v['status']=='PASS' for v in self.results.values()) else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk',type=Path,required=True,help='APK or downloaded artifact directory')
    p.add_argument('--editor',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/emulator-smoke'))
    p.add_argument('--deploy-timeout',type=int,default=600)
    p.add_argument('--adb',default='adb')
    p.add_argument('--serial')
    args = p.parse_args()
    return Smoke(args).run()


if __name__ == '__main__':
    raise SystemExit(main())
