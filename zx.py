import sqlite3
import pandas as pd
import streamlit as st

# 1. تهيئة الصفحة
st.set_page_config(
    page_title="المشاقبة - نظام إدارة المبيعات والمخزون المتقدم",
    page_icon="👑",
    layout="wide"
)

DB_NAME = "web_store.db"

# 2. إدارة قاعدة البيانات SQLite3
def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            discount REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'Cash',
            total_price REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # التحديث التلقائي لأعمدة الجداول إن لم تكن موجودة
    cursor.execute("PRAGMA table_info(sales)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'discount' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
    if 'payment_method' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
    if 'customer_name' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN customer_name TEXT DEFAULT 'عميل نقدي'")
    if 'customer_phone' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN customer_phone TEXT DEFAULT '-'")
        
    conn.commit()
    conn.close()

def add_product(name, category, price, stock):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
                   (name, category, price, stock))
    conn.commit()
    conn.close()

def get_products():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def update_product(prod_id, name, category, price, stock):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET name=?, category=?, price=?, stock=? WHERE id=?",
                   (name, category, price, stock, int(prod_id)))
    conn.commit()
    conn.close()

def delete_product(prod_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (int(prod_id),))
    conn.commit()
    conn.close()

def record_sale(c_name, c_phone, product_id, product_name, quantity, discount_val, pay_method, final_total):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, int(product_id)))
    cursor.execute('''
        INSERT INTO sales (customer_name, customer_phone, product_name, quantity, discount, payment_method, total_price) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (c_name, c_phone, product_name, quantity, discount_val, pay_method, final_total))
    sale_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sale_id

def refund_sale(sale_id, product_name, quantity):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (quantity, product_name))
    cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    conn.commit()
    conn.close()

def get_sales_history():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM sales ORDER BY date DESC", conn)
    conn.close()
    return df

init_db()

# --- إدارة الجلسة وتسجيل الدخول ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None

def login():
    st.markdown("<h2 style='text-align: center;'>🔒 تسجيل الدخول لنظام متاجر المشاقبة</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة السر", type="password")
        if st.button("دخول", type="primary", use_container_width=True):
            if username.lower() == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.user_role = "Admin"
                st.rerun()
            elif username.lower() == "cashier" and password == "cashier123":
                st.session_state.logged_in = True
                st.session_state.user_role = "Cashier"
                st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة! (جرب admin / admin123 أو cashier / cashier123)")

if not st.session_state.logged_in:
    login()
    st.stop()

# --- الهيدر الرئيسي والعلامة التجارية ---
st.markdown("<h2 style='text-align: center; color: #f59e0b;'>✨ بسم الله الرحمن الرحيم ✨</h2>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>👑 مَـتـاجِـر الـمُـشَـاقِـبَـة</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>AL-MASHAQBEH TRADING CO. - العلامة التجارية المسجلة ®</p>", unsafe_allow_html=True)

st.sidebar.markdown(f"👤 **المستخدم الحقيقي:** `{st.session_state.user_role}`")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.rerun()

st.divider()

# تحديد القوائم حسب الصلاحيات
if st.session_state.user_role == "Admin":
    menu_options = [
        "🏪 كاشير المبيعات", 
        "🚨 تنبيهات النقص", 
        "🔄 استرجاع المبيعات", 
        "📦 إدارة المخزون", 
        "📊 السجل والرسوم البيانية"
    ]
else:
    menu_options = ["🏪 كاشير المبيعات"]

menu = st.sidebar.radio("🔱 القائمة الرئيسية", menu_options)

# ----------------------------------------------------
# 1. قسم كاشير المبيعات ونظام الفواتير والخصومات
# ----------------------------------------------------
if menu == "🏪 كاشير المبيعات":
    st.header("🛒 قسم المبيعات وإصدار الفواتير")
    
    df_products = get_products()
    
    if df_products.empty:
        st.info("💡 لا توجد منتجات في المخزون حالياً.")
    else:
        col_action, col_display = st.columns([1.2, 1], gap="large")
        
        with col_action:
            st.subheader("👤 بيانات الزبون والفاتورة")
            c_name = st.text_input("اسم الزبون:", value="عميل نقدي")
            c_phone = st.text_input("رقم هاتف الزبون:", value="-")
            
            st.write("---")
            st.subheader("🛍️ تحديد المنتج")
            product_list = df_products["name"].tolist()
            selected_product_name = st.selectbox("اختر المنتج:", options=product_list, key="cashier_select")
            
            prod_info = df_products[df_products["name"] == selected_product_name].iloc[0]
            
            m1, m2 = st.columns(2)
            m1.metric("💰 سعر القطعة", f"{prod_info['price']:.2f} د.أ")
            m2.metric("📦 المخزون المتاح", f"{prod_info['stock']} قطعة")
            
            max_qty = int(prod_info['stock']) if prod_info['stock'] > 0 else 1
            qty = st.number_input("الكمية المطلوبة:", min_value=1, max_value=max_qty, value=1, disabled=(prod_info['stock'] == 0))
            
            # طريقة الدفع
            pay_method = st.selectbox("💳 طريقة الدفع:", ["نقداً (Cash)", "كليك (CliQ)", "بطاقة (Visa/Mastercard)"])
            
            # الخصم
            st.write("---")
            st.subheader("🎟️ الخصومات")
            discount_type = st.radio("نوع الخصم:", ["بدون خصم", "نسبة مئوية (%)", "مبلغ مباشر (د.أ)"], horizontal=True)
            
            discount_value = 0.0
            subtotal = qty * prod_info['price']
            
            if discount_type == "نسبة مئوية (%)":
                pct = st.number_input("نسبة الخصم (%):", min_value=0.0, max_value=100.0, value=0.0)
                discount_value = (subtotal * pct) / 100.0
            elif discount_type == "مبلغ مباشر (د.أ)":
                discount_value = st.number_input("مبلغ الخصم (د.أ):", min_value=0.0, max_value=float(subtotal), value=0.0)
            
            final_total = max(0.0, subtotal - discount_value)
            
            st.markdown(f"#### 💵 السعر الأصلي: {subtotal:.2f} د.أ")
            st.markdown(f"#### 🏷️ الخصم المطبق: <span style='color:#ef4444;'>-{discount_value:.2f} د.أ</span>", unsafe_allow_html=True)
            st.markdown(f"### 💳 الإجمالي النهائي: <span style='color:#f59e0b;'>{final_total:.2f} د.أ</span>", unsafe_allow_html=True)
            
            if st.button("✨ إتمام عملية البيع وطباعة الفاتورة", use_container_width=True, type="primary", disabled=(prod_info['stock'] == 0)):
                sale_id = record_sale(c_name, c_phone, prod_info['id'], prod_info['name'], qty, discount_value, pay_method, final_total)
                st.success(f"✅ تم تسجيل العملية بنجاح! (رقم الفاتورة: #{sale_id})")
                
                invoice_text = f"""
====================================
         👑 متاجر المشاقبة 👑
     AL-MASHAQBEH TRADING CO.
====================================
رقم الفاتورة: #{sale_id}
اسم الزبون: {c_name}
هاتف الزبون: {c_phone}
طريقة الدفع: {pay_method}
------------------------------------
المنتج: {prod_info['name']}
الكمية: {qty}
سعر القطعة: {prod_info['price']:.2f} د.أ
المجموع الفرعي: {subtotal:.2f} د.أ
الخصم: {discount_value:.2f} د.أ
الإجمالي النهائي: {final_total:.2f} د.أ
====================================
شكراً لتسوقكم معنا!
                """
                
                st.text_area("📄 معاينة الفاتورة الحرارية:", invoice_text, height=250)
                st.download_button(
                    label="🖨️ تنزيل وطباعة الفاتورة (TXT)",
                    data=invoice_text,
                    file_name=f"Invoice_{sale_id}.txt",
                    mime="text/plain"
                )

        with col_display:
            st.subheader("📋 قائمة المنتجات والبحث السريع")
            search_query = st.text_input("🔍 بحث باسم المنتج أو التصنيف...", "", key="cashier_search")
            
            if search_query:
                filtered_df = df_products[
                    df_products["name"].str.contains(search_query, case=False, na=False) | 
                    df_products["category"].str.contains(search_query, case=False, na=False)
                ]
            else:
                filtered_df = df_products

            st.dataframe(
                filtered_df[["id", "name", "category", "price", "stock"]],
                column_config={
                    "id": "المُعرّف",
                    "name": "اسم المنتج",
                    "category": "التصنيف",
                    "price": st.column_config.NumberColumn("السعر (د.أ)", format="%.2f د.أ"),
                    "stock": st.column_config.NumberColumn("المخزون المتاح"),
                },
                use_container_width=True,
                hide_index=True
            )

# ----------------------------------------------------
# 2. قسم تنبيهات النقص (🚨 Low Stock Alerts)
# ----------------------------------------------------
elif menu == "🚨 تنبيهات النقص":
    st.header("🚨 نظام تنبيهات المخزون المنخفض")
    df_products = get_products()
    
    threshold = st.slider("حدد حد التنبيه للكميات المنخفضة:", min_value=1, max_value=20, value=5)
    low_stock = df_products[df_products["stock"] <= threshold]
    
    if low_stock.empty:
        st.success("🎉 جميع المنتجات متوفرة بكميات ممتازة فوق حد التنبيه!")
    else:
        st.error(f"⚠️ يوجد ({len(low_stock)}) منتجات أوشكت على النفاد! يرجى إعادة طلبها فوراً:")
        st.dataframe(
            low_stock[["id", "name", "category", "stock"]],
            column_config={
                "id": "المُعرّف",
                "name": "اسم المنتج",
                "category": "التصنيف",
                "stock": st.column_config.NumberColumn("الكمية المتبقية ⚠️"),
            },
            use_container_width=True,
            hide_index=True
        )

# ----------------------------------------------------
# 3. قسم استرجاع المبيعات
# ----------------------------------------------------
elif menu == "🔄 استرجاع المبيعات":
    st.header("🔄 قسم استرجاع وإرجاع المبيعات")
    df_sales = get_sales_history()
    if df_sales.empty:
        st.info("لا توجد مبيعات مسجلة لإرجاعها.")
    else:
        sale_to_refund = st.selectbox(
            "اختر رقم الفاتورة لإرجاعها:", 
            options=df_sales["id"].tolist(),
            format_func=lambda x: f"فاتورة #{x} - {df_sales[df_sales['id']==x]['product_name'].values[0]}"
        )
        selected_sale = df_sales[df_sales["id"] == sale_to_refund].iloc[0]
        
        st.warning(f"⚠️ تفاصيل الفاتورة المراد إرجاعها:\n- اسم الزبون: **{selected_sale['customer_name']}**\n- المنتج: **{selected_sale['product_name']}**\n- المبلغ المسترد: **{selected_sale['total_price']:.2f} د.أ**")
        
        if st.button("❌ تأكيد استرجاع الفاتورة وإعادة الكمية للمخزن", type="primary"):
            refund_sale(selected_sale["id"], selected_sale["product_name"], int(selected_sale["quantity"]))
            st.success("✅ تم إرجاع المبلغ واستعادة الكمية للمخزون بنجاح!")
            st.rerun()

# ----------------------------------------------------
# 4. قسم إدارة المخزون
# ----------------------------------------------------
elif menu == "📦 إدارة المخزون":
    st.header("📦 إدارة المنتجات والمخزون")
    tab_add, tab_edit_delete = st.tabs(["➕ إضافة منتج جديد", "✏️ تعديل أو حذف منتج"])
    
    with tab_add:
        with st.form("add_product_form", clear_on_submit=True):
            name = st.text_input("اسم المنتج")
            category = st.text_input("التصنيف")
            price = st.number_input("السعر (د.أ)", min_value=0.0, format="%.2f")
            stock = st.number_input("الكمية المتاحة", min_value=0, step=1)
            
            submit = st.form_submit_button("إضافة المنتج إلى المخزن", type="primary")
            if submit:
                if name:
                    add_product(name, category, price, stock)
                    st.success("تمت إضافة المنتج بنجاح!")
                    st.rerun()

    with tab_edit_delete:
        df_products = get_products()
        if not df_products.empty:
            prod_to_edit = st.selectbox("اختر المنتج لتعديله أو حذفه:", df_products["name"].tolist(), key="edit_select")
            selected_row = df_products[df_products["name"] == prod_to_edit].iloc[0]
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                new_name = st.text_input("الاسم الجديد", value=selected_row["name"], key="edit_name")
                new_cat = st.text_input("التصنيف الجديد", value=selected_row["category"], key="edit_cat")
                new_price = st.number_input("السعر الجديد", value=float(selected_row["price"]), key="edit_price")
                new_stock = st.number_input("الكمية الجديدة", value=int(selected_row["stock"]), key="edit_stock")
                
                if st.button("💾 تحديث البيانات", key="btn_update", use_container_width=True):
                    update_product(selected_row["id"], new_name, new_cat, new_price, new_stock)
                    st.success("تم تحديث البيانات بنجاح!")
                    st.rerun()
            
            with col_edit2:
                st.write("---")
                if st.button("❌ حذف هذا المنتج نهائياً", type="primary", key="btn_delete", use_container_width=True):
                    delete_product(selected_row["id"])
                    st.success("تم حذف المنتج نهائياً!")
                    st.rerun()

    st.divider()
    st.subheader("📋 قائمة المخزون الحالية")
    st.dataframe(get_products(), use_container_width=True)

# ----------------------------------------------------
# 5. قسم السجل والرسوم البيانية (📊 Dashboard & Analytics)
# ----------------------------------------------------
elif menu == "📊 السجل والرسوم البيانية":
    st.header("📊 التقارير والرسوم البيانية التفاعلية")
    df_sales = get_sales_history()
    
    if df_sales.empty:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
    else:
        total_revenue = df_sales["total_price"].sum()
        total_items_sold = df_sales["quantity"].sum()
        total_discounts = df_sales["discount"].sum() if "discount" in df_sales.columns else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric(label="إجمالي صافي المبيعات", value=f"{total_revenue:.2f} د.أ")
        m2.metric(label="إجمالي القطع المباعة", value=f"{int(total_items_sold)} قطعة")
        m3.metric(label="إجمالي الخصومات", value=f"{total_discounts:.2f} د.أ")
        
        st.divider()
        st.subheader("📈 التحليلات والرسوم البيانية")
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("##### 🏆 الأكثر مبيعاً حسب المبيعات (د.أ)")
            sales_by_prod = df_sales.groupby("product_name")["total_price"].sum()
            st.bar_chart(sales_by_prod)
            
        with chart_col2:
            st.markdown("##### 💳 المبيعات حسب طريقة الدفع")
            pay_dist = df_sales.groupby("payment_method")["total_price"].sum()
            st.bar_chart(pay_dist)

        st.divider()
        st.subheader("📥 تصدير السجل")
        csv_data = df_sales.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📊 تصدير السجل المالي كملف CSV / Excel (.csv)",
            data=csv_data,
            file_name="Sales_Report_Mashaqa.csv",
            mime="text/csv",
            use_container_width=True
        )
            
        st.divider()
        st.subheader("📋 جدول الفواتير والسجلات التفصيلية")
        st.dataframe(df_sales, use_container_width=True)