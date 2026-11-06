"""Re-extract the stage templates (docx/xlsx) into assets/seed/pursuit_kit.json.

Usage: python tools/extract_kit.py "<folder with 01..09 stage subfolders>" assets/seed/pursuit_kit.json
Needs: pip install openpyxl python-docx. Re-run the seed (RESET_DB=true) afterwards.
"""
import openpyxl, glob, json, docx, datetime, sys, os
root, outp = sys.argv[1], os.path.abspath(sys.argv[2])
os.chdir(root)
out=[]
def cell(v):
    if v is None: return ""
    if isinstance(v,float): return round(v,2)
    if isinstance(v,(datetime.date,datetime.datetime)): return v.strftime("%Y-%m-%d")
    return v
for f in sorted(glob.glob("*/*.xlsx")+glob.glob("*/*.docx")):
    stage,name=f.split("/")
    rec={"stage":stage,"file":name,"format":name.rsplit('.',1)[1],"sample":name.startswith("Sample"),"sheets":[]}
    if f.endswith(".xlsx"):
        wb=openpyxl.load_workbook(f,data_only=True)
        for ws in wb.worksheets:
            rows=[[cell(v) for v in r] for r in ws.iter_rows(values_only=True)]
            hi=next((i for i,r in enumerate(rows) if sum(1 for v in r if v!="")>=3),None)
            if hi is None:
                pre=[r for r in rows if any(v!="" for v in r)]
                data=[[v for v in r if v!=""] for r in pre[2:]]
                rec["sheets"].append({"name":ws.title,"title":pre[0][0],"guidance":pre[1][0] if len(pre)>1 else "","columns":["Item","Value"],"rows":[d[:2] for d in data if d]}); continue
            pre=[next((v for v in r if v!=""),"") for r in rows[:hi] if any(v!="" for v in r)]
            hdr=rows[hi]; n=max(i for i,v in enumerate(hdr) if v!="")+1
            cols=[str(v) if v!="" else f"Col {i+1}" for i,v in enumerate(hdr[:n])]
            data=[r[:n] for r in rows[hi+1:] if any(v!="" for v in r[:n])]
            rec["sheets"].append({"name":ws.title,"title":pre[0] if pre else ws.title,"guidance":" ".join(str(x) for x in pre[1:]),"columns":cols,"rows":data})
    else:
        d=docx.Document(f); lines=[p.text.strip() for p in d.paragraphs if p.text.strip()]
        secs=[]; cur=[]
        for l in lines[2:]:
            if l=="[Write here]": secs.append([cur[0]," ".join(cur[1:]),""]); cur=[]
            else: cur.append(l)
        rec["sheets"].append({"name":"Sections","title":lines[0],"guidance":lines[1],"columns":["Section","Guidance","Response"],"rows":secs})
    out.append(rec)
json.dump(out,open(outp,"w"),indent=1,ensure_ascii=False,default=str)
print([(r["file"],len(r["sheets"])) for r in out])
