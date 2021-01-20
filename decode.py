import os
import sys
import magic


def main(args):
    target = '.'
    if len(args) >= 2:
        target = args[1]
    if not os.path.exists(target):
        print('[!] Target %s is not Found' % target)

    for root, _, files in os.walk(target):
        for f in files:
            fn = os.path.join(root, f)
            try:
                tp = magic.from_file(fn)
            except:
                continue
            if tp.startswith('C source') or 'ISO-8859 text' in tp:
                line = '[*] Decode %s' % fn
                print(line, end='')
                with open(fn, 'rb') as f:
                    data = f.read()
                try:
                    try:
                        text = data.decode('gb18030')
                    except:
                        text = data.decode('utf-8')
                    data = text.encode('utf-8')
                    with open(fn, 'wb') as f:
                        f.write(data)
                    status = '.' * (70 - len(line)) + 'Success'
                    print(status)
                except:
                    status = '.' * (70 - len(line)) + 'Failed'
                    print(status)


if __name__ == '__main__':
    main(sys.argv)

