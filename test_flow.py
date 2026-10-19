import sys; sys.path.insert(0, '.')
from datetime import date, timedelta
from app import create_app
from app.config import Config
from app.extensions import db
from app.models import *

class T(Config):
    TESTING=True; SQLALCHEMY_DATABASE_URI="sqlite:///:memory:"; WTF_CSRF_ENABLED=False

app=create_app(T)
with app.app_context():
    a=User(username="admin",email="a@a",full_name="Admin",role="admin"); a.set_password("x")
    r=User(username="r1",email="r@r",full_name="R1"); r.set_password("123456")
    c=Category(name="IT"); b=Book(title="B",author="A",category=c,total_copies=1,available_copies=1)
    db.session.add_all([a,r,c,b]); db.session.commit()

cl=app.test_client()
def login(u,p): return cl.post("/login",data={"username":u,"password":p},follow_redirects=True)
def ok(resp,txt=None):
    assert resp.status_code==200,(resp.status_code,resp.data[:300]); 
    if txt: assert txt in resp.get_data(as_text=True),txt
    return resp

for url in ["/","/books/1","/login","/register","/api/v1/books","/api/v1/books/1"]: ok(cl.get(url))
assert cl.get("/admin/").status_code==302
ok(login("r1","123456"))
assert cl.get("/admin/").status_code==403
ok(cl.post("/books/1/borrow",follow_redirects=True),"Đã gửi yêu cầu")
ok(cl.post("/books/1/borrow",follow_redirects=True),"đã mượn hoặc đã gửi")
ok(cl.get("/my/loans"),"Chờ duyệt")
cl.post("/logout"); ok(login("admin","x"))
for u in ["/admin/","/admin/loans","/admin/loans?status=overdue","/admin/books","/admin/books/new","/admin/books/1/edit","/admin/categories","/admin/users","/admin/fines","/api/v1/stats"]: ok(cl.get(u))
ok(cl.post("/admin/loans/1/approve",follow_redirects=True),"Đã duyệt")
with app.app_context():
    assert db.session.get(Book,1).available_copies==0
    l=db.session.get(Loan,1); l.due_date=date.today()-timedelta(days=3); db.session.commit()
ok(cl.post("/admin/loans/1/return",follow_redirects=True),"15,000")
with app.app_context():
    assert db.session.get(Book,1).available_copies==1
cl.post("/logout"); ok(login("r1","123456"))
ok(cl.post("/books/1/borrow",follow_redirects=True),"tiền phạt chưa nộp")
cl.post("/logout"); ok(login("admin","x"))
ok(cl.post("/admin/fines/1/pay",follow_redirects=True),"thu tiền phạt")
ok(cl.post("/admin/books/new",data={"title":"New","author":"X","total_copies":"3"},follow_redirects=True),"Đã lưu")
ok(cl.post("/admin/categories",data={"name":"Mới"},follow_redirects=True),"Đã thêm")
ok(cl.post("/admin/users/2/toggle",follow_redirects=True),"Đã khoá")
print("TẤT CẢ KIỂM THỬ ĐẠT")
