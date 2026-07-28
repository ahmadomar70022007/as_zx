import streamlit as st
import sqlite3
import pandas as pd
import datetime

# ----------------------------------------------------
# 1. إعدادات الصفحة وقاعدة البيانات
# ----------------------------------------------------
st.set_page_config(
    page_title="متاجر المشاقبة - نظام إدارة المبيعات والمخزون",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "mashaqba_pos.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جدول المنتجات
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            cost_price REAL NOT NULL,
            stock INTEGER NOT NULL,
            min_stock INTEGER DEFAULT 5
        )
    ''')
    
    # جدول المبيعات
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            customer_name TEXT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            net_profit REAL NOT NULL,
            payment_method TEXT NOT NULL
        )
    ''')

    # جدول الذمم والديون
    c.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            notes TEXT
        )
    ''')

    # جدول المستخدمين والصلاحيات
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # إضافة حسابات افتراضية إن كانت قاعدة البيانات جديدة
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "Admin"))
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("cashier1", "1234", "Cashier"))
        
    conn.commit()
    conn.close()

init_db()

# ----------------------------------------------------
# 2. إعداد جلسة المستخدم (Session State)
# ----------------------------------------------------
if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = "admin"
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "Admin"
if "cart" not in st.session_state:
    st.session_state["cart"] = []

# ----------------------------------------------------
# 3. القائمة الجانبية والصلاحيات
# ----------------------------------------------------
st.sidebar.title("👑 متاجر المشاقبة")
st.sidebar.markdown(f"**المستخدم الحالي:** `{st.session_state['logged_user']}`")
st.sidebar.markdown(f"**الصلاحية:** `{st.session_state['user_role']}`")

if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state["logged_user"] = "admin"
    st.session_state["user_role"] = "Admin"
    st.rerun()

st.sidebar.write("---")

current_role = st.session_state.get("user_role", "Cashier")

# تحديد القوائم المتاحة حسب الصلاحية
if current_role == "Admin":
    menu_options = [
        "🛒 كاشير المبيعات المطور",
        "🚨 تنبيهات النقص المتقدمة",
        "📙 سجل الذمم والديون المطور",
        "🔄 استرجاع المبيعات المطور",
        "📦 إدارة المخزون المطور",
        "🏷️ طباعة بطاقات الأسعار",
        "📊 السجل والتقارير المتقدمة",
        "⚙️ النسخ الاحتياطي والنظام",
        "👥 إدارة المستخدمين والصلاحيات"
    ]
elif current_role == "Inventory":
    menu_options = [
        "📦 إدارة المخزون المطور",
        "🚨 تنبيهات النقص المتقدمة",
        "🏷️ طباعة بطاقات الأسعار",
        "👥 إدارة المستخدمين والصلاحيات"
    ]
else:  # Cashier
    menu_options = [
        "🛒 كاشير المبيعات المطور",
        "🔄 استرجاع المبيعات المطور",
        "👥 إدارة المستخدمين والصلاحيات"
    ]

menu = st.sidebar.radio("القائمة الرئيسية 🔱", menu_options)

# دوال جلب البيانات
def get_products():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

# ----------------------------------------------------
# 1. كاشير المبيعات المطور
# ----------------------------------------------------
if menu == "🛒 كاشير المبيعات المطور":
    st.header("🛒 نقطة البيع السريعة (POS)")
    df_products = get_products()

    if df_products.empty:
        st.warning("⚠️ لا توجد منتجات بالمخزن. أضف منتجات من قسم 'إدارة المخزون' أولاً.")
    else:
        col_scan, col_cart = st.columns([1, 1.2])

        with col_scan:
            st.subheader("🔍 إضافة مواد للسلة")
            selected_product_name = st.selectbox("اختر المنتج:", df_products["name"].tolist())
            product_info = df_products[df_products["name"] == selected_product_name].iloc[0]
            
            st.info(f"💵 السعر: {product_info['price']:.2f} د.أ | 📦 المتوفر بالمخزن: {product_info['stock']}")
            qty_to_add = st.number_input("الكمية المطلوب بيعها:", min_value=1, max_value=int(product_info['stock']) if product_info['stock'] > 0 else 1, value=1)
            
            if st.button("➕ إضافة للسلة", type="primary"):
                if product_info['stock'] < qty_to_add:
                    st.error("الكمية المطلوبة غير متوفرة في المخزن!")
                else:
                    st.session_state["cart"].append({
                        "id": product_info['id'],
                        "name": product_info['name'],
                        "price": product_info['price'],
                        "cost_price": product_info['cost_price'],
                        "quantity": qty_to_add,
                        "total": product_info['price'] * qty_to_add,
                        "profit": (product_info['price'] - product_info['cost_price']) * qty_to_add
                    })
                    st.success(f"تمت إضافة {product_info['name']} للسلة!")

        with col_cart:
            st.subheader("🛒 سلة المشتريات الحالية")
            if not st.session_state["cart"]:
                st.write("السلة فارغة حالياً.")
            else:
                cart_df = pd.DataFrame(st.session_state["cart"])
                st.dataframe(cart_df[["name", "price", "quantity", "total"]], use_container_width=True, hide_index=True)
                
                grand_total = cart_df["total"].sum()
                st.markdown(f"### 💳 المجموع الإجمالي: `{grand_total:.2f} د.أ`")
                
                cust_name = st.text_input("اسم الزبون (اختياري):", value="زبون عام")
                pay_method = st.radio("طريقة الدفع:", ["نقداً (Cash)", "بطاقة (Card)", "ذمم / دين"], horizontal=True)

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ إتمام عملية البيع والطبع", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        for item in st.session_state["cart"]:
                            # تسجيل البيع
                            c.execute("""
                                INSERT INTO sales (date, customer_name, product_name, quantity, total_price, net_profit, payment_method)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (now_str, cust_name, item['name'], item['quantity'], item['total'], item['profit'], pay_method))
                            
                            # خصم المخزون
                            c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item['quantity'], item['id']))
                        
                        # إذا كان الدفع ديناً
                        if pay_method == "ذمم / دين":
                            c.execute("INSERT INTO debts (customer_name, amount, date, notes) VALUES (?, ?, ?, ?)", 
                                      (cust_name, grand_total, now_str, f"فاتورة شراء بتاريخ {now_str}"))
                        
                        conn.commit()
                        conn.close()
                        st.session_state["cart"] = []
                        st.success("🎉 تم إتمام العملية وخصم الكميات بنجاح!")
                        st.rerun()

                with col_btn2:
                    if st.button("🗑️ تفريغ السلة", use_container_width=True):
                        st.session_state["cart"] = []
                        st.rerun()

# ----------------------------------------------------
# 2. تنبيهات النقص المتقدمة
# ----------------------------------------------------
elif menu == "🚨 تنبيهات النقص المتقدمة":
    st.header("🚨 تنبيهات النقص ومراقبة المخزون الحرج")
    conn = sqlite3.connect(DB_NAME)
    df_low = pd.read_sql_query("SELECT barcode, name, category, stock, min_stock FROM products WHERE stock <= min_stock", conn)
    conn.close()

    if df_low.empty:
        st.balloons()
        st.success("✅ جميع المنتجات في المخزن بكميات آمنة وفوق حد الأمان!")
    else:
        st.error(f"⚠️ يوجد ({len(df_low)}) منتجات وصلت أو قلت عن الحد الأدنى المحدد!")
        st.dataframe(df_low, column_config={
            "barcode": "الباركود",
            "name": "اسم المنتج",
            "category": "التصنيف",
            "stock": "المتوفر حالياً",
            "min_stock": "حد النقص الأدنى"
        }, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 3. سجل الذمم والديون
# ----------------------------------------------------
elif menu == "📙 سجل الذمم والديون المطور":
    st.header("📙 سجل متابعة الذمم والديون")
    conn = sqlite3.connect(DB_NAME)
    df_debts = pd.read_sql_query("SELECT * FROM debts", conn)
    conn.close()

    if df_debts.empty:
        st.info("💡 لا توجد ديون مسجلة حالياً.")
    else:
        st.dataframe(df_debts, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 4. استرجاع المبيعات
# ----------------------------------------------------
elif menu == "🔄 استرجاع المبيعات المطور":
    st.header("🔄 قسم إرجاع واستبدال المبيعات")
    conn = sqlite3.connect(DB_NAME)
    df_sales = pd.read_sql_query("SELECT * FROM sales ORDER BY id DESC LIMIT 20", conn)
    conn.close()
    
    st.write("آخر 20 عملية بيع:")
    st.dataframe(df_sales, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 5. إدارة المخزون المطور
# ----------------------------------------------------
elif menu == "📦 إدارة المخزون المطور":
    st.header("📦 إدارة المنتجات والمخزون")
    
    with st.expander("➕ إضافة منتج جديد للمخزن", expanded=True):
        with st.form("add_prod_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                p_code = st.text_input("رمز الباركود:")
                p_name = st.text_input("اسم المنتج:")
            with c2:
                p_cat = st.text_input("التصنيف:", value="عام")
                p_price = st.number_input("سعر البيع (د.أ):", min_value=0.01, step=0.1)
            with c3:
                p_cost = st.number_input("سعر التكلفة (د.أ):", min_value=0.0, step=0.1)
                p_stock = st.number_input("الكمية المتاحة:", min_value=1, value=10)

            if st.form_submit_button("💾 حفظ المنتج", type="primary"):
                if p_code and p_name:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("INSERT INTO products (barcode, name, category, price, cost_price, stock) VALUES (?, ?, ?, ?, ?, ?)",
                                  (p_code, p_name, p_cat, p_price, p_cost, p_stock))
                        conn.commit()
                        conn.close()
                        st.success("تم إضافة المنتج بنجاح!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("الباركود موجود بالفعل لمنتج آخر!")

    st.subheader("📋 المنتجات المسجلة")
    st.dataframe(get_products(), use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 6. طباعة بطاقات الأسعار
# ----------------------------------------------------
elif menu == "🏷️ طباعة بطاقات الأسعار":
    st.header("🏷️ استوديو تصميم وطباعة ملصقات الأسعار والرفوف الاحترافي")
    df_products = get_products()
    
    if df_products.empty:
        st.info("💡 لا توجد منتجات بالمخزن حالياً لتوليد ملصقات لها.")
    else:
        col_opt1, col_opt2, col_opt3 = st.columns(3)
        
        with col_opt1:
            selected_tag_prod = st.selectbox("🎯 اختر المنتج المراد طباعة بطاقته:", df_products["name"].tolist())
            prod_data = df_products[df_products["name"] == selected_tag_prod].iloc[0]
            
        with col_opt2:
            tag_style = st.selectbox("🎨 اختر نمط وقالب البطاقة:", [
                "🥇 القالب الذهبي الفاخر (Premium Gold)",
                "💥 قالب العروض والتخفيضات (Special Promo)",
                "🌿 القالب العصري البسيط (Modern Minimal)"
            ])
            
        with col_opt3:
            tag_size = st.radio("📐 حجم البطاقة:", ["صغير للرفوف (Small)", "كبير للملصقات (Large)"], horizontal=True)

        card_width = "380px" if "كبير" in tag_size else "280px"
        font_size_price = "42px" if "كبير" in tag_size else "32px"

        st.divider()
        st.subheader("🖼️ معاينة البطاقة قبل الطباعة")

        p_name = prod_data['name']
        p_cat = prod_data['category']
        p_price = f"{prod_data['price']:.2f}"
        p_code = prod_data['barcode']
        p_id = prod_data['id']

        if "الذهبي" in tag_style:
            tag_html = f"""
            <div style="border: 2px solid #d97706; background: #111827; padding: 16px; border-radius: 14px; width: {card_width}; text-align: center; margin: auto; font-family: sans-serif; color: white;">
                <div style="border-bottom: 1px solid #374151; padding-bottom: 6px; margin-bottom: 10px;">
                    <span style="color: #f59e0b; font-weight: bold; font-size: 14px;">👑 متاجر المشاقبة</span>
                </div>
                <h3 style="color: #ffffff; margin: 6px 0; font-size: 20px;">{p_name}</h3>
                <p style="color: #9ca3af; font-size: 12px; margin: 0 0 10px 0;">التصنيف: {p_cat}</p>
                <div style="background: rgba(245, 158, 11, 0.15); border: 1px dashed #f59e0b; padding: 8px; border-radius: 10px; margin: 10px 0;">
                    <span style="color: #10b981; font-size: {font_size_price}; font-weight: bold;">{p_price}</span>
                    <span style="color: #10b981; font-size: 16px; font-weight: bold;"> د.أ</span>
                </div>
                <div style="font-size: 11px; color: #9ca3af; margin-top: 8px;">
                    الباركود: {p_code} | المعرف: #{p_id}
                </div>
            </div>
            """
        elif "العروض" in tag_style:
            tag_html = f"""
            <div style="border: 3px solid #ef4444; background: #ffffff; padding: 16px; border-radius: 14px; width: {card_width}; text-align: center; margin: auto; font-family: sans-serif; color: #111827;">
                <div style="background-color: #ef4444; color: white; font-weight: bold; font-size: 13px; padding: 4px 0; border-radius: 6px; margin-bottom: 8px;">
                    🔥 عرض خاص 🔥
                </div>
                <h3 style="color: #111827; margin: 6px 0; font-size: 20px;">{p_name}</h3>
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 8px 0;">👑 متاجر المشاقبة</p>
                <div style="background-color: #fef2f2; border: 2px solid #fca5a5; padding: 8px; border-radius: 10px; margin: 8px 0;">
                    <span style="color: #dc2626; font-size: {font_size_price}; font-weight: bold;">{p_price}</span>
                    <span style="color: #dc2626; font-size: 16px; font-weight: bold;"> د.أ</span>
                </div>
                <div style="font-size: 11px; color: #9ca3af; margin-top: 6px;">
                    كود: {p_code}
                </div>
            </div>
            """
        else:
            tag_html = f"""
            <div style="border: 1px solid #d1d5db; background: #f9fafb; padding: 16px; border-radius: 12px; width: {card_width}; text-align: center; margin: auto; font-family: sans-serif; color: #111827;">
                <h4 style="color: #4b5563; margin: 0 0 4px 0; font-size: 13px;">👑 متاجر المشاقبة</h4>
                <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 6px 0;">
                <h3 style="color: #1f2937; margin: 6px 0; font-size: 19px;">{p_name}</h3>
                <h2 style="color: #059669; font-size: {font_size_price}; margin: 8px 0; font-weight: bold;">
                    {p_price} <span style="font-size:15px;">د.أ</span>
                </h2>
                <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">
                    رمز المنتج: {p_code}
                </div>
            </div>
            """

        st.markdown(tag_html, unsafe_allow_html=True)
        st.write("---")
        
        print_code = f"""
        <html>
        <head>
            <title>طباعة بطاقة - {p_name}</title>
            <style>
                body {{ display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: white; }}
                @page {{ size: auto; margin: 0; }}
            </style>
        </head>
        <body onload="window.print(); window.close();">
            {tag_html}
        </body>
        </html>
        """
        
        st.download_button(
            label="🖨️ تنزيل بطاقة السعر لطباعتها (HTML)",
            data=print_code,
            file_name=f"PriceTag_{p_id}.html",
            mime="text/html",
            type="primary",
            use_container_width=True
        )

# ----------------------------------------------------
# 7. السجل والتقارير المتقدمة
# ----------------------------------------------------
elif menu == "📊 السجل والتقارير المتقدمة":
    st.header("📊 التقارير الأرباح والأداء المالي")
    conn = sqlite3.connect(DB_NAME)
    df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()

    if df_sales.empty:
        st.info("لا توجد مبيعات مسجلة في التقرير.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("إجمالي المبيعات", f"{df_sales['total_price'].sum():.2f} د.أ")
        m2.metric("صافي الأرباح", f"{df_sales['net_profit'].sum():.2f} د.أ")
        m3.metric("عدد الفواتير", len(df_sales))

        st.divider()
        st.dataframe(
            df_sales,
            column_config={
                "id": "رقم الفاتورة",
                "date": "التاريخ والوقت",
                "customer_name": "الزبون",
                "product_name": "المنتج",
                "quantity": "الكمية",
                "total_price": st.column_config.NumberColumn("إجمالي الصافي", format="%.2f د.أ"),
                "net_profit": st.column_config.NumberColumn("صافي الربح", format="%.2f د.أ"),
                "payment_method": "طريقة الدفع"
            },
            use_container_width=True,
            hide_index=True
        )

        csv_export = df_sales.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 تصدير التقرير المالي الحالي إلى CSV/Excel",
            data=csv_export,
            file_name=f"Financial_Report_{datetime.date.today()}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

# ----------------------------------------------------
# 8. النسخ الاحتياطي والنظام
# ----------------------------------------------------
elif menu == "⚙️ النسخ الاحتياطي والنظام":
    st.header("⚙️ أدوات النظام والنسخ الاحتياطي")
    try:
        with open(DB_NAME, "rb") as db_file:
            st.download_button(
                "💾 تنزيل نسخة احتياطية من قاعدة البيانات (Backup)",
                data=db_file,
                file_name=f"mashaqba_pos_backup_{datetime.date.today()}.db",
                mime="application/x-sqlite3",
                type="primary",
                use_container_width=True
            )
    except Exception as e:
        st.error(f"خطأ في إعداد النسخة الاحتياطية: {e}")

# ----------------------------------------------------
# 9. قسم إدارة المستخدمين والحسابات والصلاحيات
# ----------------------------------------------------
elif menu == "👥 إدارة المستخدمين والصلاحيات":
    st.header("👥 مركز إدارة الحسابات، الأمان، وتحديد الصلاحيات")
    
    curr_user = st.session_state.get("logged_user", "admin")
    curr_role = st.session_state.get("user_role", "Admin")

    tab_my_acc, tab_add_u, tab_manage_u = st.tabs([
        "🔐 حسابي (تغيير كلمة السر/الاسم)", 
        "➕ إضافة مستخدم جديد", 
        "🛠️ إدارة الحسابات والصلاحيات"
    ])

    # 1. إعدادات الحساب الشخصي
    with tab_my_acc:
        st.subheader("🔑 إعدادات الحساب الشخصي")
        st.info(f"المستخدم الحالي: **{curr_user}** | الصلاحية: **{curr_role}**")
        
        with st.form("my_account_form"):
            new_my_user = st.text_input("👤 اسم المستخدم الجديد:", value=curr_user)
            new_my_pass = st.text_input("🔑 كلمة السر الجديدة (اتركها فارغة بدون تغيير):", type="password")
            confirm_my_pass = st.text_input("🔒 تأكيد كلمة السر الجديدة:", type="password")
            
            if st.form_submit_button("💾 حفظ التحديثات", type="primary"):
                if new_my_pass and (new_my_pass != confirm_my_pass):
                    st.error("⚠️ كلمة السر وتأكيدها غير متطابقين!")
                else:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    try:
                        if new_my_pass:
                            c.execute("UPDATE users SET username=?, password=? WHERE username=?", (new_my_user, new_my_pass, curr_user))
                        else:
                            c.execute("UPDATE users SET username=? WHERE username=?", (new_my_user, curr_user))
                        
                        conn.commit()
                        st.session_state["logged_user"] = new_my_user
                        st.success("✅ تم تحديث بيانات حسابك بنجاح!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("⚠️ اسم المستخدم هذا مستخدم بالفعل، اختر اسماً آخر.")
                    finally:
                        conn.close()

    # 2. إضافة مستخدم جديد
    with tab_add_u:
        if curr_role != "Admin":
            st.warning("⛔ إضافة مستخدمين جدد مقتصرة على مدير النظام (Admin).")
        else:
            st.subheader("➕ إضافة موظف/مستخدم جديد للنظام")
            with st.form("add_user_form", clear_on_submit=True):
                add_u = st.text_input("👤 اسم المستخدم الجديد:")
                add_p = st.text_input("🔑 كلمة السر:", type="password")
                add_r = st.selectbox("🛡️ صلاحيات الوصول والمستوى:", [
                    "Cashier (كاشير - المبيعات والإرجاع فقط)",
                    "Inventory (مدير المخزن - المنتجات والرفوف فقط)",
                    "Admin (مدير نظام - صلاحيات كاملة)"
                ])
                
                if st.form_submit_button("➕ إنشاء الحساب", type="primary"):
                    role_code = "Admin" if "Admin" in add_r else ("Inventory" if "Inventory" in add_r else "Cashier")
                    if add_u and add_p:
                        try:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (add_u, add_p, role_code))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ تم إنشاء حساب ({add_u}) بصلاحية [{role_code}] بنجاح!")
                        except sqlite3.IntegrityError:
                            st.error("⚠️ اسم المستخدم هذا موجود بالفعل!")
                    else:
                        st.warning("⚠️ يرجى تعبئة كافة الحقول المطلوب.")

    # 3. إدارة وتعديل المستخدمين
    with tab_manage_u:
        if curr_role != "Admin":
            st.warning("⛔ إدارة صلاحيات الموظفين مقتصرة على مدير النظام (Admin).")
        else:
            st.subheader("📋 قائمة المستخدمين المسجلين")
            conn = sqlite3.connect(DB_NAME)
            df_u = pd.read_sql_query("SELECT id, username, role FROM users", conn)
            conn.close()
            
            st.dataframe(df_u, column_config={
                "id": "المعرف",
                "username": "اسم المستخدم",
                "role": "الصلاحية الحالية"
            }, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("⚙️ تعديل أو إعادة ضبط حساب موظف")
            
            target_user = st.selectbox("اختر الموظف للتعديل عليه:", df_u["username"].tolist())
            
            if target_user:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT role FROM users WHERE username=?", (target_user,))
                user_curr_role = c.fetchone()[0]
                conn.close()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    updated_role = st.selectbox("تغيير الصلاحية:", ["Admin", "Cashier", "Inventory"], index=["Admin", "Cashier", "Inventory"].index(user_curr_role))
                    if st.button("🔄 تحديث الصلاحية"):
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("UPDATE users SET role=? WHERE username=?", (updated_role, target_user))
                        conn.commit()
                        conn.close()
                        st.success(f"تم تغيير صلاحية {target_user} إلى {updated_role}")
                        st.rerun()

                with col2:
                    reset_pass = st.text_input(f"تغيير كلمة سر ({target_user}):", type="password")
                    if st.button("🔑 تعيين كلمة السر الجديدة"):
                        if reset_pass:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("UPDATE users SET password=? WHERE username=?", (reset_pass, target_user))
                            conn.commit()
                            conn.close()
                            st.success(f"تم تغيير كلمة السر للحساب {target_user} بنجاح!")
                        else:
                            st.warning("اكتب كلمة السر الجديدة أولاً.")

                st.write("---")
                if target_user != "admin":
                    if st.button(f"🗑️ حذف حساب {target_user} نهائياً", type="secondary"):
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("DELETE FROM users WHERE username=?", (target_user,))
                        conn.commit()
                        conn.close()
                        st.success(f"تم حذف حساب {target_user}!")
                        st.rerun()