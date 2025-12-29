# ================== IMPORTS ==================
import sys, csv, sqlite3
from datetime import datetime
from functools import partial

from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QTextOption

DB = "tasks.db"

# ================== SPLASH ==================
class Splash(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(420, 220)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        frame = QFrame(self)
        frame.setGeometry(0, 0, 420, 220)
        frame.setStyleSheet("QFrame{background:#121212;border-radius:14px;color:white;}")

        layout = QVBoxLayout(frame)
        layout.addStretch()

        title = QLabel("به برنامه مدیریت تسک خوش آمدید")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar {background:#1e1e1e;border-radius:3px;}
            QProgressBar::chunk {background:#3a7afe;border-radius:3px;}
        """)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.progress)
        layout.addStretch()

        self.val = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(25)

    def update(self):
        self.val += 2
        self.progress.setValue(self.val)
        if self.val >= 100:
            self.timer.stop()

# ================== VIEW TASK ==================
class ViewTaskDialog(QDialog):
    def __init__(self, task):
        super().__init__()
        self.setWindowTitle("مشاهده تسک")
        self.resize(500, 400)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        fields = [
            ("عنوان", task[1]),
            ("توضیح", task[2]),
            ("زمان", task[3]),
            ("دسته", task[4]),
            ("اولویت", task[5]),
            ("تاریخ ایجاد", datetime.fromtimestamp(task[6]).strftime("%Y-%m-%d %H:%M")),
            ("وضعیت", "✔ انجام شده" if task[7] else "⏳ انجام نشده"),
        ]

        for k, v in fields:
            if k == "توضیح":
                txt = QTextEdit(str(v))
                txt.setReadOnly(True)
                txt.setWordWrapMode(QTextOption.WordWrap)
                txt.setMaximumHeight(200)
                form.addRow(k + ":", txt)
            else:
                lbl = QLabel(str(v))
                lbl.setWordWrap(True)
                form.addRow(k + ":", lbl)

        layout.addLayout(form)
        btn = QPushButton("بستن")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

# ================== MAIN APP ==================
class TaskManager(QWidget):
    PRIORITY_COLORS = {"زیاد": "#ff5555", "متوسط": "#ffaa00", "کم": "#55ff55"}

    def __init__(self):
        super().__init__()
        self.editing_id = None
        self.page = 1
        self.page_size = 20

        self.db = sqlite3.connect(DB)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.create_db()
        self.init_ui()
        self.load_categories()
        self.load_tasks()

    # ---------- DB ----------
    def create_db(self):
        c = self.db.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            time TEXT,
            category TEXT,
            priority TEXT CHECK(priority IN ('زیاد','متوسط','کم')),
            created INTEGER,
            done INTEGER DEFAULT 0
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_search ON tasks(title,description,category)")
        self.db.commit()

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle("Task Manager Pro")
        self.resize(1150, 680)
        self.setLayoutDirection(Qt.RightToLeft)

        self.setStyleSheet("""
        QWidget{background:#121212;color:white;font-family:Segoe UI;}
        QLineEdit,QTextEdit,QComboBox{background:#1e1e1e;border-radius:6px;padding:6px;}
        QPushButton{background:#3a7afe;border-radius:6px;padding:8px;}
        QPushButton:hover{background:#5a95ff;}
        QHeaderView::section{background:#252525;}
        """)

        main = QVBoxLayout(self)

        # TOP BAR
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 جستجو...")
        self.search.textChanged.connect(self.reset_and_load)
        self.stats = QLabel()
        exit_btn = QPushButton("❌ خروج")
        exit_btn.clicked.connect(self.close)
        top.addWidget(self.search, 3)
        top.addWidget(self.stats, 1)
        top.addWidget(exit_btn)
        main.addLayout(top)

        # CONTENT
        content = QHBoxLayout()
        main.addLayout(content)

        # LEFT PANEL
        left = QVBoxLayout()
        content.addLayout(left, 3)

        self.title = QLineEdit()
        self.title.setPlaceholderText("عنوان")
        self.desc = QTextEdit()
        self.time = QLineEdit()
        self.time.setPlaceholderText("زمان تخمینی")
        self.cat = QComboBox()
        self.priority = QComboBox()
        self.priority.addItems(["زیاد","متوسط","کم"])

        self.add_btn = QPushButton("➕ افزودن")
        self.add_btn.clicked.connect(self.add_task)
        self.save_btn = QPushButton("💾 ذخیره")
        self.save_btn.clicked.connect(self.save_edit)
        self.save_btn.hide()
        self.cancel_btn = QPushButton("لغو")
        self.cancel_btn.clicked.connect(self.cancel_edit)
        self.cancel_btn.hide()

        left.addWidget(self.title)
        left.addWidget(self.desc)
        left.addWidget(self.time)
        left.addWidget(self.cat)
        left.addWidget(self.priority)
        left.addWidget(self.add_btn)
        left.addWidget(self.save_btn)
        left.addWidget(self.cancel_btn)

        self.new_cat = QLineEdit()
        self.new_cat.setPlaceholderText("دسته جدید")
        cat_btn = QPushButton("➕")
        cat_btn.clicked.connect(self.add_category)
        h = QHBoxLayout()
        h.addWidget(self.new_cat)
        h.addWidget(cat_btn)
        left.addLayout(h)
        left.addStretch()

        # TABLE
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["✓","عنوان","توضیح","زمان","دسته","اولویت","تاریخ","ID"]
        )
        self.table.hideColumn(7)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.cellDoubleClicked.connect(self.start_edit)
        content.addWidget(self.table, 7)

        # PAGINATION
        pag = QHBoxLayout()
        self.prev_btn = QPushButton("⬅ قبلی")
        self.next_btn = QPushButton("بعدی ➡")
        self.page_lbl = QLabel()
        self.size_combo = QComboBox()
        self.size_combo.addItems(["20","50"])
        self.size_combo.currentTextChanged.connect(self.change_page_size)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        pag.addWidget(QLabel("نمایش:"))
        pag.addWidget(self.size_combo)
        pag.addStretch()
        pag.addWidget(self.prev_btn)
        pag.addWidget(self.page_lbl)
        pag.addWidget(self.next_btn)
        main.addLayout(pag)

        # BOTTOM
        bottom = QHBoxLayout()
        exp = QPushButton("📤 CSV")
        exp.clicked.connect(self.export_csv)
        delb = QPushButton("🗑 حذف")
        delb.clicked.connect(self.delete_task)
        view = QPushButton("👁 مشاهده")
        view.clicked.connect(self.view_task)
        bottom.addWidget(exp)
        bottom.addWidget(delb)
        bottom.addWidget(view)
        main.addLayout(bottom)

    # ---------- LOGIC ----------
    def load_tasks(self):
        self.table.setRowCount(0)
        txt = self.search.text()
        q = f"%{txt}%"
        offset = (self.page - 1) * self.page_size

        total = self.db.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE (title LIKE ? OR description LIKE ? OR category LIKE ?)
        """, (q,q,q)).fetchone()[0]

        done = self.db.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE done=1 AND (title LIKE ? OR description LIKE ? OR category LIKE ?)
        """, (q,q,q)).fetchone()[0]

        self.total_pages = max(1, (total + self.page_size - 1)//self.page_size)

        cur = self.db.execute("""
        SELECT * FROM tasks
        WHERE (title LIKE ? OR description LIKE ? OR category LIKE ?)
        ORDER BY created DESC
        LIMIT ? OFFSET ?
        """, (q,q,q,self.page_size,offset))

        for r,row in enumerate(cur):
            self.table.insertRow(r)

            chk = QCheckBox()
            chk.blockSignals(True)
            chk.setChecked(bool(row[7]))
            chk.blockSignals(False)
            chk.stateChanged.connect(partial(self.toggle_done, row[0]))
            self.table.setCellWidget(r,0,chk)

            for c,val in enumerate(row[1:7],1):
                it = QTableWidgetItem(str(val))
                if not row[7]:
                    it.setForeground(QColor(self.PRIORITY_COLORS.get(row[5],"white")))
                else:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r,c,it)

            self.table.setItem(r,7,QTableWidgetItem(str(row[0])))

        self.stats.setText(f"✔ {done} / {total}")
        self.page_lbl.setText(f"صفحه {self.page} از {self.total_pages}")

    def toggle_done(self, tid, _):
        self.db.execute("UPDATE tasks SET done=1-done WHERE id=?", (tid,))
        self.db.commit()
        self.load_tasks()

    def add_task(self):
        if not self.title.text().strip():
            QMessageBox.warning(self,"خطا","عنوان خالی است")
            return
        self.db.execute("""
        INSERT INTO tasks(title,description,time,category,priority,created)
        VALUES(?,?,?,?,?,?)
        """,(
            self.title.text(),
            self.desc.toPlainText(),
            self.time.text(),
            self.cat.currentText() if self.cat.count() else "",
            self.priority.currentText(),
            int(datetime.now().timestamp())
        ))
        self.db.commit()
        self.clear()
        self.reset_and_load()

    def start_edit(self,r,c):
        if c == 0:
            return
        self.editing_id = self.table.item(r,7).text()
        self.title.setText(self.table.item(r,1).text())
        self.desc.setText(self.table.item(r,2).text())
        self.time.setText(self.table.item(r,3).text())
        self.cat.setCurrentText(self.table.item(r,4).text())
        self.priority.setCurrentText(self.table.item(r,5).text())
        self.add_btn.setDisabled(True)
        self.save_btn.show()
        self.cancel_btn.show()

    def save_edit(self):
        self.db.execute("""
        UPDATE tasks SET title=?,description=?,time=?,category=?,priority=?
        WHERE id=?
        """,(
            self.title.text(),
            self.desc.toPlainText(),
            self.time.text(),
            self.cat.currentText(),
            self.priority.currentText(),
            self.editing_id
        ))
        self.db.commit()
        self.cancel_edit()
        self.load_tasks()

    def cancel_edit(self):
        self.editing_id = None
        self.clear()
        self.save_btn.hide()
        self.cancel_btn.hide()
        self.add_btn.setDisabled(False)

    def delete_task(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        if QMessageBox.question(self,"حذف","آیا مطمئن هستید؟") != QMessageBox.Yes:
            return
        ids = [(self.table.item(r.row(),7).text(),) for r in rows]
        self.db.executemany("DELETE FROM tasks WHERE id=?", ids)
        self.db.commit()
        self.reset_and_load()

    def view_task(self):
        rows = self.table.selectionModel().selectedRows()
        if len(rows) != 1:
            QMessageBox.information(self,"خطا","یک تسک انتخاب کنید")
            return
        tid = self.table.item(rows[0].row(),7).text()
        task = self.db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if task:
            ViewTaskDialog(task).exec()

    def export_csv(self):
        path,_ = QFileDialog.getSaveFileName(self,"CSV","tasks.csv","CSV (*.csv)")
        if not path:
            return
        with open(path,"w",newline="",encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["عنوان","توضیح","زمان","دسته","اولویت","تاریخ","وضعیت"])
            for r in self.db.execute("SELECT title,description,time,category,priority,created,done FROM tasks"):
                w.writerow([
                    r[0], r[1], r[2], r[3], r[4],
                    datetime.fromtimestamp(r[5]).strftime("%Y-%m-%d %H:%M"),
                    "✔" if r[6] else "⏳"
                ])
        QMessageBox.information(self,"موفق","ذخیره شد")

    def add_category(self):
        if not self.new_cat.text().strip():
            return
        try:
            self.db.execute("INSERT INTO categories(name) VALUES(?)",(self.new_cat.text(),))
            self.db.commit()
            self.new_cat.clear()
            self.load_categories()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self,"خطا","دسته تکراری است")

    def load_categories(self):
        self.cat.clear()
        for (n,) in self.db.execute("SELECT name FROM categories ORDER BY name"):
            self.cat.addItem(n)

    def clear(self):
        self.title.clear()
        self.desc.clear()
        self.time.clear()

    def reset_and_load(self):
        self.page = 1
        self.load_tasks()

    def change_page_size(self,v):
        self.page_size = int(v)
        self.reset_and_load()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.load_tasks()

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            self.load_tasks()

    def closeEvent(self,e):
        self.db.close()
        e.accept()

# ================== RUN ==================
app = QApplication(sys.argv)
splash = Splash()
splash.show()
main_window = TaskManager()

def start():
    splash.close()
    main_window.show()

QTimer.singleShot(1200, start)
sys.exit(app.exec())