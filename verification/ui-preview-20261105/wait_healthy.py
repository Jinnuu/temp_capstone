import json,subprocess,time,sys,pathlib
names=['snp-ui-preview-db-1','snp-ui-preview-web-1','snp-ui-preview-proxy-1']
start=time.monotonic()
for attempt in range(120):
    data=json.loads(subprocess.check_output(['docker','inspect',*names]))
    health={x['Name'].strip('/'):x['State'].get('Health',{}).get('Status') for x in data}
    if all(v=='healthy' for v in health.values()):
        if len(sys.argv)>1:pathlib.Path(sys.argv[1]).write_text(json.dumps({'passed':True,'poll_wait_seconds':round(time.monotonic()-start,1),'health':health},indent=2))
        print('PREVIEW_ALL_HEALTHY',flush=True)
        break
    time.sleep(2)
else:raise SystemExit(str(health))
