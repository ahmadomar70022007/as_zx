import sqlite3
import pandas as pd
import streamlit as st
import datetime

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
    
    # التحديث التلقائي لأعمدة الجداول
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

# --- إدارة الجلسة وتسجيل الدخول المضمون ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "cart" not in st.session_state:
    st.session_state["cart"] = []

def check_credentials(user, pwd):
    user = user.strip().lower()
    pwd = pwd.strip()
    if user == "admin" and pwd == "admin123":
        return "Admin"
    elif user == "cashier" and pwd == "cashier123":
        return "Cashier"
    return None

if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center;'>🔒 تسجيل الدخول لنظام متاجر المشاقبة</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form_unique"):
            username_input = st.text_input("اسم المستخدم")
            password_input = st.text_input("كلمة السر", type="password")
            submit = st.form_submit_button("دخول", type="primary", use_container_width=True)
            
            if submit:
                role = check_credentials(username_input, password_input)
                if role:
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = role
                    st.success("✅ تم تسجيل الدخول بنجاح!")
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة السر غير صحيحة")
    st.stop()

# --- الهيدر الرئيسي والعلامة التجارية ---
st.markdown("<h2 style='text-align: center; color: #f59e0b;'>✨ بسم الله الرحمن الرحيم ✨</h2>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>👑 مَـتـاجِـر الـمُـشَـاقِـبَـة</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>AL-MASHAQBEH TRADING CO. - العلامة التجارية المسجلة ®</p>", unsafe_allow_html=True)

st.sidebar.markdown(f"👤 **المستخدم الحالي:** `{st.session_state['user_role']}`")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["cart"] = []
    st.rerun()

st.divider()

# القوائم المتاحة حسب الصلاحيات
if st.session_state["user_role"] == "Admin":
    menu_options = [
        "🏪 كاشير المبيعات المطور", 
        "🚨 تنبيهات النقص", 
        "💳 سجل الذمم والديون",
        "🔄 استرجاع المبيعات", 
        "📦 إدارة المخزون", 
        "🏷️ طباعة بطاقات الأسعار",
        "📊 السجل والتقارير المتقدمة",
        "⚙️ النسخ الاحتياطي والنظام"
    ]
else:
    menu_options = ["🏪 كاشير المبيعات المطور"]

menu = st.sidebar.radio("🔱 القائمة الرئيسية", menu_options)

# ----------------------------------------------------
# 1. قسم كاشير المبيعات المطور والمميز جداً
# ----------------------------------------------------
if menu == "🏪 كاشير المبيعات المطور":
    st.header("🛒 نقطة البيع الذكية (Smart POS Cashier)")
    df_products = get_products()
    
    if df_products.empty:
        st.info("💡 لا توجد منتجات بالمخزن حالياً، يرجى إضافتها أولاً.")
    else:
        col_products, col_cart = st.columns([1.4, 1], gap="large")
        
        # --- القسم الأيسر: تصفح المنتجات والبحث السريع ---
        with col_products:
            st.subheader("📦 المنتجات المتاحة")
            
            search_q = st.text_input("🔍 بحث سريع عن منتج بالاسم أو التصنيف...", key="pos_search")
            if search_q:
                filtered_prods = df_products[df_products["name"].str.contains(search_q, case=False, na=False) | df_products["category"].str.contains(search_q, case=False, na=False)]
            else:
                filtered_prods = df_products
                
            st.write("---")
            
            # اختيارات إضافة منتج إلى السلة
            selected_p_name = st.selectbox("🎯 اختر المنتج للتفاصيل والإضافة:", filtered_prods["name"].tolist(), key="select_prod_cart")
            p_data = df_products[df_products["name"] == selected_p_name].iloc[0]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 سعر القطعة", f"{p_data['price']:.2f} د.أ")
            m2.metric("📦 المتوفر بالمخزن", f"{p_data['stock']} قطعة")
            
            if p_data['stock'] == 0:
                m3.metric("الحالة", "❌ نافد", delta_color="inverse")
            elif p_data['stock'] <= 5:
                m3.metric("الحالة", "⚠️ منخفض", delta_color="off")
            else:
                m3.metric("الحالة", "✅ ممتاز")

            # شريط نسبة المخزون المتبقي
            stock_pct = min(1.0, float(p_data['stock']) / 50.0) if p_data['stock'] > 0 else 0.0
            st.caption("مؤشر نسبة المخزون المتاح:")
            st.progress(stock_pct)

            max_q = int(p_data['stock']) if p_data['stock'] > 0 else 1
            add_qty = st.number_input("الكمية المراد إضافتها للسلة:", min_value=1, max_value=max_q, value=1, disabled=(p_data['stock'] == 0))
            
            if st.button("➕ إضافة المنتج إلى سلة المشتريات", type="primary", use_container_width=True, disabled=(p_data['stock'] == 0)):
                # إضافة للسلة
                st.session_state["cart"].append({
                    "id": p_data["id"],
                    "name": p_data["name"],
                    "price": float(p_data["price"]),
                    "qty": int(add_qty),
                    "total": float(p_data["price"] * add_qty)
                })
                st.success(f"إضافة ({add_qty}) من [{p_data['name']}] إلى السلة بنجاح!")
                st.rerun()

            st.write("---")
            st.subheader("📋 جدول استعراض المخزون")
            st.dataframe(filtered_prods[["id", "name", "category", "price", "stock"]], use_container_width=True, hide_index=True)

        # --- القسم الأيمن: سلة المشتريات والحسابات والطباعة ---
        with col_cart:
            st.subheader("🛒 سلة الفاتورة الحالية")
            
            if not st.session_state["cart"]:
                st.info("🛒 السلة فارغة حالياً. قم باختيار المنتجات وإضافتها السلة.")
            else:
                cart_df = pd.DataFrame(st.session_state["cart"])
                st.dataframe(cart_df[["name", "qty", "price", "total"]], column_config={
                    "name": "المنتج",
                    "qty": "الكمية",
                    "price": st.column_config.NumberColumn("السعر", format="%.2f د.أ"),
                    "total": st.column_config.NumberColumn("الإجمالي", format="%.2f د.أ")
                }, use_container_width=True, hide_index=True)

                if st.button("🗑️ تفريغ السلة بالكامل", type="secondary"):
                    st.session_state["cart"] = []
                    st.rerun()

                st.write("---")
                st.subheader("👤 بيانات الزبون وطريقة الدفع")
                c_name = st.text_input("اسم الزبون:", value="عميل نقدي", key="cart_cname")
                c_phone = st.text_input("رقم هاتف الزبون:", value="-", key="cart_cphone")
                
                pay_method = st.selectbox("💳 طريقة الدفع:", ["نقداً (Cash)", "كليك (CliQ)", "بطاقة (Visa)", "آجل / ذمم (Credit)"])
                
                # حساب المبالغ والخصم
                raw_cart_total = sum(item["total"] for item in st.session_state["cart"])
                
                st.write("---")
                st.subheader("🎟️ الخصم المطبق")
                disc_type = st.radio("نوع الخصم:", ["بدون خصم", "نسبة (%)", "مبلغ (د.أ)"], horizontal=True, key="cart_disc_type")
                
                discount_val = 0.0
                if disc_type == "نسبة (%)":
                    p_disc = st.number_input("النسبة (%):", min_value=0.0, max_value=100.0, value=0.0)
                    discount_val = (raw_cart_total * p_disc) / 100.0
                elif disc_type == "مبلغ (د.أ)":
                    discount_val = st.number_input("المبلغ (د.أ):", min_value=0.0, max_value=float(raw_cart_total), value=0.0)

                final_cart_total = max(0.0, raw_cart_total - discount_val)

                # حاسبة الباقي
                if "نقداً" in pay_method:
                    p_col, c_col = st.columns(2)
                    with p_col:
                        paid_amount = st.number_input("💵 المدفوع (د.أ):", min_value=0.0, value=float(final_cart_total))
                    with c_col:
                        change_amt = max(0.0, paid_amount - final_cart_total)
                        st.metric("🪙 الباقي للزبون", f"{change_amt:.2f} د.أ")
                else:
                    paid_amount = final_cart_total
                    change_amt = 0.0

                st.markdown(f"#### 💵 الفرعي: `{raw_cart_total:.2f} د.أ` | 🏷️ الخصم: <span style='color:#ef4444;'>-{discount_val:.2f} د.أ</span>", unsafe_allow_html=True)
                st.markdown(f"### 💳 صافي الفاتورة: <span style='color:#f59e0b;'>{final_cart_total:.2f} د.أ</span>", unsafe_allow_html=True)

                if st.button("✨ اعتماد وإتمام الفاتورة وطباعتها", type="primary", use_container_width=True):
                    # تسجيل المبيعات لكل المنتجات في السلة
                    last_sale_id = None
                    items_summary_txt = ""
                    for item in st.session_state["cart"]:
                        sale_id = record_sale(c_name, c_phone, item["id"], item["name"], item["qty"], discount_val, pay_method, item["total"])
                        last_sale_id = sale_id
                        items_summary_txt += f"{item['name']} (x{item['qty']}) - {item['total']:.2f} د.أ\n"
                    
                    st.success("✅ تم إتمام وتخزين جميع عناصر الفاتورة بنجاح!")
                    
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    invoice_text = f"""
========================================
         👑 متاجر المشاقبة 👑
     AL-MASHAQBEH TRADING CO.
========================================
التاريخ: {now_str}
رقم الفاتورة: #{last_sale_id}
اسم الزبون: {c_name}
هاتف الزبون: {c_phone}
طريقة الدفع: {pay_method}
----------------------------------------
المنتجات المشتراة:
{items_summary_txt}----------------------------------------
المجموع الفرعي: {raw_cart_total:.2f} د.أ
الخصم المطبق: {discount_val:.2f} د.أ
الصافي النهائي: {final_cart_total:.2f} د.أ
المبلغ المدفوع: {paid_amount:.2f} د.أ
الباقي للزبون: {change_amt:.2f} د.أ
========================================
    شكراً لتسوقكم معنا! نتمنى لكم يوماً سعيداً
                    """
                    
                    st.text_area("📄 معاينة الإيصال الحراري:", invoice_text, height=270)
                    st.download_button("🖨️ تنزيل وطباعة الإيصال (TXT)", data=invoice_text, file_name=f"Receipt_{last_sale_id}.txt", mime="text/plain")
                    
                    # تفريغ السلة بعد البيع
                    st.session_state["cart"] = []

# ----------------------------------------------------
# 2. تنبيهات النقص
# ----------------------------------------------------
elif menu == "🚨 تنبيهات النقص":
    st.header("🚨 نظام تنبيهات المخزون المنخفض")
    df_products = get_products()
    threshold = st.slider("حدد حد التنبيه للكميات المنخفضة:", min_value=1, max_value=20, value=5)
    low_stock = df_products[df_products["stock"] <= threshold]
    
    if low_stock.empty:
        st.success("🎉 جميع المنتجات متوفرة بكميات ممتازة!")
    else:
        st.error(f"⚠️ يوجد ({len(low_stock)}) منتجات أوشكت على النفاد:")
        st.dataframe(low_stock[["id", "name", "category", "stock"]], use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 3. سجل الذمم والديون
# ----------------------------------------------------
elif menu == "💳 سجل الذمم والديون":
    st.header("💳 سجل المبيعات الآجلة والذمم")
    df_sales = get_sales_history()
    credit_sales = df_sales[df_sales["payment_method"].str.contains("آجل", na=False)]
    
    if credit_sales.empty:
        st.success("🎉 لا توجد ديون آحلة على الزبائن حالياً!")
    else:
        st.warning(f"⚠️ إجمالي الديون القائمة: **{credit_sales['total_price'].sum():.2f} د.أ**")
        st.dataframe(credit_sales[["id", "customer_name", "customer_phone", "product_name", "quantity", "total_price", "date"]], use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 4. استرجاع المبيعات
# ----------------------------------------------------
elif menu == "🔄 استرجاع المبيعات":
    st.header("🔄 قسم استرجاع المبيعات")
    df_sales = get_sales_history()
    if df_sales.empty:
        st.info("لا توجد مبيعات مسجلة لإرجاعها.")
    else:
        sale_to_refund = st.selectbox("اختر رقم الفاتورة لإرجاعها:", options=df_sales["id"].tolist())
        selected_sale = df_sales[df_sales["id"] == sale_to_refund].iloc[0]
        st.warning(f"تفاصيل الفاتورة المراد إرجاعها: **{selected_sale['product_name']}** (المبلغ: **{selected_sale['total_price']:.2f} د.أ**)")
        if st.button("❌ تأكيد استرجاع الفاتورة", type="primary"):
            refund_sale(selected_sale["id"], selected_sale["product_name"], int(selected_sale["quantity"]))
            st.success("✅ تم إرجاع المبلغ واستعادة الكمية للمخزون بنجاح!")
            st.rerun()

# ----------------------------------------------------
# 5. إدارة المخزون
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
            if submit and name:
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
                new_name = st.text_input("الاسم الجديد", value=selected_row["name"])
                new_cat = st.text_input("التصنيف الجديد", value=selected_row["category"])
                new_price = st.number_input("السعر الجديد", value=float(selected_row["price"]))
                new_stock = st.number_input("الكمية الجديدة", value=int(selected_row["stock"]))
                if st.button("💾 تحديث البيانات", use_container_width=True):
                    update_product(selected_row["id"], new_name, new_cat, new_price, new_stock)
                    st.success("تم التحديث بنجاح!")
                    st.rerun()
            with col_edit2:
                st.write("---")
                if st.button("❌ حذف المنتج نهائياً", type="primary", use_container_width=True):
                    delete_product(selected_row["id"])
                    st.success("تم الحذف بنجاح!")
                    st.rerun()

    st.divider()
    st.dataframe(get_products(), use_container_width=True)

# ----------------------------------------------------
# 6. طباعة بطاقات الأسعار والملصقات
# ----------------------------------------------------
elif menu == "🏷️ طباعة بطاقات الأسعار":
    st.header("🏷️ مولد ملصقات الأسعار والرفوف (Price Tags)")
    df_products = get_products()
    
    if df_products.empty:
        st.info("لا توجد منتجات بالمخزن لتوليد ملصقات لها.")
    else:
        selected_tag_prod = st.selectbox("اختر المنتج لتوليد الملصق:", df_products["name"].tolist())
        prod_data = df_products[df_products["name"] == selected_tag_prod].iloc[0]
        
        st.write("---")
        st.subheader("🖼️ معاينة تصميم بطاقة السعر (Shelf Tag)")
        
        tag_html = f"""
        <div style="border: 3px dashed #f59e0b; padding: 20px; border-radius: 12px; width: 320px; text-align: center; background-color: #1f2937; margin: auto;">
            <h3 style="color: #f59e0b; margin: 0;">👑 متاجر المشاقبة</h3>
            <p style="color: #9ca3af; font-size: 12px; margin-bottom: 10px;">AL-MASHAQBEH TRADING</p>
            <hr style="border-color: #374151;">
            <h2 style="color: #ffffff; margin: 10px 0;">{prod_data['name']}</h2>
            <p style="color: #9ca3af; margin: 0;">التصنيف: {prod_data['category']}</p>
            <h1 style="color: #10b981; font-size: 38px; margin: 15px 0;">{prod_data['price']:.2f} <span style="font-size:18px;">د.أ</span></h1>
            <p style="color: #6b7280; font-size: 11px;">مُعرّف المنتج: #{prod_data['id']}</p>
        </div>
        """
        st.markdown(tag_html, unsafe_allow_html=True)

# ----------------------------------------------------
# 7. السجل والتقارير المتقدمة
# ----------------------------------------------------
elif menu == "📊 السجل والتقارير المتقدمة":
    st.header("📊 السجل المالي والتحليلات الزمانية وأوقات الذروة")
    df_sales = get_sales_history()
    
    if df_sales.empty:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
    else:
        df_sales["date_dt"] = pd.to_datetime(df_sales["date"])
        date_filter = st.radio("اختر الفترة:", ["الكل", "اليوم", "آخر 7 أيام", "هذا الشهر"], horizontal=True)
        today = datetime.datetime.now().date()
        
        if date_filter == "اليوم":
            df_filtered = df_sales[df_sales["date_dt"].dt.date == today]
        elif date_filter == "آخر 7 أيام":
            df_filtered = df_sales[df_sales["date_dt"].dt.date >= (today - datetime.timedelta(days=7))]
        elif date_filter == "هذا الشهر":
            df_filtered = df_sales[(df_sales["date_dt"].dt.month == today.month) & (df_sales["date_dt"].dt.year == today.year)]
        else:
            df_filtered = df_sales
            
        m1, m2, m3 = st.columns(3)
        m1.metric("صافي الأرباح", f"{df_filtered['total_price'].sum():.2f} د.أ")
        m2.metric("القطع المباعة", f"{int(df_filtered['quantity'].sum())} قطعة")
        m3.metric("الخصومات الممنوحة", f"{df_filtered['discount'].sum():.2f} د.أ")
        
        st.divider()
        st.subheader("⏰ تحليل أوقات الذروة وساعات البيع (Peak Hours)")
        df_filtered["hour"] = df_filtered["date_dt"].dt.hour
        hourly_sales = df_filtered.groupby("hour")["total_price"].sum()
        st.line_chart(hourly_sales)
        
        st.divider()
        st.subheader("🏆 أفضل المنتجات أداءً ومبيعات")
        top_col1, top_col2 = st.columns(2)
        
        with top_col1:
            st.markdown("##### 🥇 الأكثر مبيعاً (من حيث الإيرادات)")
            top_revenue = df_filtered.groupby("product_name")["total_price"].sum().sort_values(ascending=False).head(5)
            st.dataframe(top_revenue)
            
        with top_col2:
            st.markdown("##### 📦 الأكثر طلباً (من حيث عدد القطع)")
            top_qty = df_filtered.groupby("product_name")["quantity"].sum().sort_values(ascending=False).head(5)
            st.dataframe(top_qty)

        st.divider()
        csv_data = df_filtered.drop(columns=["date_dt", "hour"], errors="ignore").to_csv(index=False).encode('utf-8-sig')
        st.download_button("📊 تصدير السجل (.csv)", data=csv_data, file_name="Sales_Report.csv", mime="text/csv", use_container_width=True)
        st.dataframe(df_filtered.drop(columns=["date_dt", "hour"], errors="ignore"), use_container_width=True)

# ----------------------------------------------------
# 8. النسخ الاحتياطي والنظام
# ----------------------------------------------------
elif menu == "⚙️ النسخ الاحتياطي والنظام":
    st.header("⚙️ أدوات النظام والنسخ الاحتياطي")
    try:
        with open(DB_NAME, "rb") as db_file:
            st.download_button("💾 تحميل النسخة الاحتياطية (.db)", data=db_file.read(), file_name="web_store_backup.db", mime="application/x-sqlite3", type="primary")
    except Exception as e:
        st.error(f"خطأ في الوصول لقاعدة البيانات: {e}")