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
            cost_price REAL DEFAULT 0,
            stock INTEGER NOT NULL,
            barcode TEXT,
            supplier TEXT,
            expiry_date TEXT,
            min_alert INTEGER DEFAULT 5
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
    sales_cols = [column[1] for column in cursor.fetchall()]
    if 'discount' not in sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
    if 'payment_method' not in sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
    if 'customer_name' not in sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN customer_name TEXT DEFAULT 'عميل نقدي'")
    if 'customer_phone' not in sales_cols:
        cursor.execute("ALTER TABLE sales ADD COLUMN customer_phone TEXT DEFAULT '-'")

    cursor.execute("PRAGMA table_info(products)")
    prod_cols = [column[1] for column in cursor.fetchall()]
    if 'cost_price' not in prod_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN cost_price REAL DEFAULT 0")
    if 'barcode' not in prod_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN barcode TEXT DEFAULT '-'")
    if 'supplier' not in prod_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN supplier TEXT DEFAULT '-'")
    if 'expiry_date' not in prod_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN expiry_date TEXT DEFAULT '-'")
    if 'min_alert' not in prod_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN min_alert INTEGER DEFAULT 5")
        
    conn.commit()
    conn.close()

def add_product(name, category, price, cost_price, stock, barcode, supplier, expiry_date, min_alert):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (name, category, price, cost_price, stock, barcode, supplier, expiry_date, min_alert) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, category, price, cost_price, stock, barcode, supplier, expiry_date, min_alert))
    conn.commit()
    conn.close()

def get_products():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def update_product(prod_id, name, category, price, cost_price, stock, barcode, supplier, expiry_date, min_alert):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE products 
        SET name=?, category=?, price=?, cost_price=?, stock=?, barcode=?, supplier=?, expiry_date=?, min_alert=? 
        WHERE id=?
    ''', (name, category, price, cost_price, stock, barcode, supplier, expiry_date, min_alert, int(prod_id)))
    conn.commit()
    conn.close()

def quick_add_stock(prod_id, added_qty):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (added_qty, int(prod_id)))
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

def update_sale_debt(sale_id, new_total, is_paid=False):
    conn = get_connection()
    cursor = conn.cursor()
    if is_paid:
        cursor.execute("UPDATE sales SET total_price = 0, payment_method = 'نقداً (تم تسديد الدين)' WHERE id = ?", (sale_id,))
    else:
        cursor.execute("UPDATE sales SET total_price = ? WHERE id = ?", (new_total, sale_id))
    conn.commit()
    conn.close()

def refund_sale_advanced(sale_id, product_name, qty_to_refund, refund_amount, return_to_stock=True, is_full_refund=True):
    conn = get_connection()
    cursor = conn.cursor()
    
    if return_to_stock:
        cursor.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (qty_to_refund, product_name))
    
    if is_full_refund:
        cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    else:
        cursor.execute("""
            UPDATE sales 
            SET quantity = quantity - ?, 
                total_price = total_price - ? 
            WHERE id = ?
        """, (qty_to_refund, refund_amount, sale_id))
        
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
        "🚨 تنبيهات النقص المتقدمة", 
        "💳 سجل الذمم والديون المطور",
        "🔄 استرجاع المبيعات المطور", 
        "📦 إدارة المخزون المطور", 
        "🏷️ طباعة بطاقات الأسعار",
        "📊 السجل والتقارير المتقدمة",
        "⚙️ النسخ الاحتياطي والنظام"
    ]
else:
    menu_options = ["🏪 كاشير المبيعات المطور", "🔄 استرجاع المبيعات المطور"]

menu = st.sidebar.radio("🔱 القائمة الرئيسية", menu_options)

# ----------------------------------------------------
# 1. قسم كاشير المبيعات المطور
# ----------------------------------------------------
if menu == "🏪 كاشير المبيعات المطور":
    st.header("🛒 نقطة البيع الذكية (Smart POS Cashier)")
    df_products = get_products()
    
    if df_products.empty:
        st.info("💡 لا توجد منتجات بالمخزن حالياً، يرجى إضافتها أولاً.")
    else:
        col_products, col_cart = st.columns([1.4, 1], gap="large")
        
        with col_products:
            st.subheader("📦 المنتجات المتاحة")
            search_q = st.text_input("🔍 بحث سريع عن منتج بالاسم، التصنيف، أو الباركود...", key="pos_search")
            if search_q:
                filtered_prods = df_products[
                    df_products["name"].str.contains(search_q, case=False, na=False) | 
                    df_products["category"].str.contains(search_q, case=False, na=False) |
                    df_products["barcode"].astype(str).str.contains(search_q, case=False, na=False)
                ]
            else:
                filtered_prods = df_products
                
            st.write("---")
            selected_p_name = st.selectbox("🎯 اختر المنتج للتفاصيل والإضافة:", filtered_prods["name"].tolist(), key="select_prod_cart")
            p_data = df_products[df_products["name"] == selected_p_name].iloc[0]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 سعر البيع", f"{p_data['price']:.2f} د.أ")
            m2.metric("📦 المتوفر بالمخزن", f"{p_data['stock']} قطعة")
            
            min_thresh = int(p_data['min_alert']) if p_data['min_alert'] else 5
            if p_data['stock'] == 0:
                m3.metric("الحالة", "❌ نافد", delta_color="inverse")
            elif p_data['stock'] <= min_thresh:
                m3.metric("الحالة", "⚠️ منخفض جداً", delta_color="off")
            else:
                m3.metric("الحالة", "✅ ممتاز")

            stock_pct = min(1.0, float(p_data['stock']) / 50.0) if p_data['stock'] > 0 else 0.0
            st.caption("مؤشر نسبة المخزون المتاح:")
            st.progress(stock_pct)

            max_q = int(p_data['stock']) if p_data['stock'] > 0 else 1
            add_qty = st.number_input("الكمية المراد إضافتها للسلة:", min_value=1, max_value=max_q, value=1, disabled=(p_data['stock'] == 0))
            
            if st.button("➕ إضافة المنتج إلى سلة المشتريات", type="primary", use_container_width=True, disabled=(p_data['stock'] == 0)):
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
            st.dataframe(filtered_prods[["id", "barcode", "name", "category", "price", "stock"]], use_container_width=True, hide_index=True)

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
                    st.session_state["cart"] = []

# ----------------------------------------------------
# 2. قسم تنبيهات النقص المتقدمة
# ----------------------------------------------------
elif menu == "🚨 تنبيهات النقص المتقدمة":
    st.header("🚨 مراقبة وإدارة تنبيهات المخزون المنخفض")
    df_products = get_products()
    
    if df_products.empty:
        st.info("💡 لا توجد منتجات بالمخزن حالياً.")
    else:
        out_of_stock = df_products[df_products["stock"] == 0]
        low_stock = df_products[(df_products["stock"] > 0) & (df_products["stock"] <= df_products["min_alert"])]
        all_alert_products = df_products[df_products["stock"] <= df_products["min_alert"]]

        ind1, ind2, ind3 = st.columns(3)
        ind1.metric("🔴 منتجات نافدة تماماً", f"{len(out_of_stock)} منتج", delta_color="inverse")
        ind2.metric("🟡 منتجات أوشكت على النفاد", f"{len(low_stock)} منتج", delta_color="off")
        ind3.metric("📦 مجموع المنتجات للتزويد", f"{len(all_alert_products)} منتج")

        st.divider()

        if all_alert_products.empty:
            st.balloons()
            st.success("🎉 ممتاز جداً! جميع المنتجات في المخزن متوفرة بكميات كافية وأعلى من الحدود الدنيا للإنذار.")
        else:
            if not out_of_stock.empty:
                st.error("🚨 **منتجات نافدة تماماً من المخزن (0 قطعة):**")
                st.dataframe(out_of_stock[["id", "barcode", "name", "category", "price", "stock", "supplier"]], use_container_width=True, hide_index=True)
                st.write("---")

            if not low_stock.empty:
                st.warning(f"⚠️ **منتجات منخفضة (تتطلب شحنة جديدة):**")
                st.dataframe(low_stock[["id", "barcode", "name", "category", "price", "stock", "min_alert", "supplier"]], use_container_width=True, hide_index=True)
                st.write("---")

            st.subheader("⚡ إعادة تزويد الشحنات بنقرة واحدة (Quick Restock)")
            col_re1, col_re2, col_re3 = st.columns([2, 1, 1])
            with col_re1:
                selected_alert_p = st.selectbox("اختر المنتج الناقص لشحنه فوراً:", all_alert_products["name"].tolist())
                selected_alert_info = df_products[df_products["name"] == selected_alert_p].iloc[0]
            with col_re2:
                add_stock_qty = st.number_input("الكمية المضافة للمخزن:", min_value=1, value=10, step=1)
            with col_re3:
                st.write(" ")
                st.write(" ")
                if st.button("➕ شحن المخزن الآن", type="primary", use_container_width=True):
                    quick_add_stock(selected_alert_info["id"], add_stock_qty)
                    st.success(f"✅ تم إضافة ({add_stock_qty}) قطعة إلى [{selected_alert_p}] بنجاح!")
                    st.rerun()

            st.write("---")
            reorder_csv = all_alert_products[["id", "barcode", "name", "category", "stock", "min_alert", "supplier"]].to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 تنزيل قائمة الطلبيات للموردين (.csv)", data=reorder_csv, file_name="Reorder_Stock_List.csv", mime="text/csv", type="secondary")

# ----------------------------------------------------
# 3. قسم سجل الذمم والديون المطور
# ----------------------------------------------------
elif menu == "💳 سجل الذمم والديون المطور":
    st.header("💳 نظام إدارة وتجميع الذمم وسداد الديون")
    df_sales = get_sales_history()
    credit_sales = df_sales[(df_sales["payment_method"].str.contains("آجل", na=False)) & (df_sales["total_price"] > 0)]
    
    if credit_sales.empty:
        st.balloons()
        st.success("🎉 ممتاز! لا توجد أي ديون أو ذمم آحلة قائمة على الزبائن حالياً.")
    else:
        total_credit = credit_sales["total_price"].sum()
        unique_debtors = credit_sales["customer_name"].nunique()
        max_debt = credit_sales["total_price"].max()

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 إجمالي الذمم القائمة", f"{total_credit:.2f} د.أ")
        kpi2.metric("👥 عدد العملاء المدينين", f"{unique_debtors} عميل")
        kpi3.metric("⚠️ أكبر دين مسجل", f"{max_debt:.2f} د.أ")

        st.divider()

        search_debtor = st.text_input("🔍 بحث عن عميل بالاسم أو رقم الهاتف:", key="debt_search")
        if search_debtor:
            filtered_credit = credit_sales[
                credit_sales["customer_name"].str.contains(search_debtor, case=False, na=False) |
                credit_sales["customer_phone"].str.contains(search_debtor, case=False, na=False)
            ]
        else:
            filtered_credit = credit_sales

        st.subheader("📋 قائمة الفواتير الآجلة غير المسددة")
        st.dataframe(
            filtered_credit[["id", "customer_name", "customer_phone", "product_name", "quantity", "total_price", "date"]],
            column_config={
                "id": "رقم الفاتورة",
                "customer_name": "اسم العميل",
                "customer_phone": "الهاتف",
                "product_name": "المنتج",
                "quantity": "الكمية",
                "total_price": st.column_config.NumberColumn("المبلغ المستحق", format="%.2f د.أ"),
                "date": "التاريخ"
            },
            use_container_width=True, hide_index=True
        )

        st.divider()

        st.subheader("💵 محطة تسديد وسداد الذمم (Debt Payment)")
        col_pay1, col_pay2 = st.columns([1.2, 1], gap="large")
        
        with col_pay1:
            sale_debt_id = st.selectbox("اختر رقم الفاتورة الآجلة للتسديد:", options=filtered_credit["id"].tolist())
            selected_debt = filtered_credit[filtered_credit["id"] == sale_debt_id].iloc[0]
            
            st.info(f"👤 العميل: **{selected_debt['customer_name']}** | 📱 الهاتف: **{selected_debt['customer_phone']}**")
            st.warning(f"📌 المنتج: **{selected_debt['product_name']}** | المبلغ المستحق: **{selected_debt['total_price']:.2f} د.أ**")
            
            pay_type = st.radio("نوع التسديد:", ["سداد كامل (إغلاق الذمة)", "سداد جزئي (دفعة من الدين)"], horizontal=True)
            
            if pay_type == "سداد جزئي (دفعة من الدين)":
                paid_part = st.number_input("المبلغ المدفوع الآن (د.أ):", min_value=0.1, max_value=float(selected_debt['total_price']), value=float(selected_debt['total_price'] / 2))
                rem_debt = selected_debt['total_price'] - paid_part
                st.write(f"💵 المتبقي من الدين بعد الدفعة: **{rem_debt:.2f} د.أ**")
            else:
                paid_part = selected_debt['total_price']
                rem_debt = 0.0

            if st.button("✨ اعتماد وتأكيد عملية التسديد", type="primary", use_container_width=True):
                if pay_type == "سداد كامل (إغلاق الذمة)":
                    update_sale_debt(selected_debt['id'], 0, is_paid=True)
                    st.success(f"✅ تم تسديد الفاتورة #{selected_debt['id']} بالكامل وتم إغلاق الذمة!")
                else:
                    update_sale_debt(selected_debt['id'], rem_debt, is_paid=False)
                    st.success(f"✅ تم تسجيل دفعة بقيمة ({paid_part:.2f} د.أ) المتبقي الآن: ({rem_debt:.2f} د.أ)")

                now_pay_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                pay_receipt = f"""
========================================
         👑 متاجر المشاقبة 👑
      إيصال تسديد دين / سند قبض
========================================
التاريخ: {now_pay_str}
رقم الفاتورة الأصلية: #{selected_debt['id']}
اسم العميل: {selected_debt['customer_name']}
رقم الهاتف: {selected_debt['customer_phone']}
----------------------------------------
المبلغ المدفوع الآن: {paid_part:.2f} د.أ
المبلغ المتبقي ذمة: {rem_debt:.2f} د.أ
----------------------------------------
توقيع المستلم: __________________
========================================
        شكراً لالتزامكم بالتسديد!
                """
                st.session_state["last_pay_receipt"] = pay_receipt
                st.rerun()

        with col_pay2:
            st.subheader("📄 معاينة سند القبض والإيصال")
            if "last_pay_receipt" in st.session_state:
                st.text_area("معاينة سند التسديد:", st.session_state["last_pay_receipt"], height=260)
                st.download_button("🖨️ تنزيل سند القبض (TXT)", data=st.session_state["last_pay_receipt"], file_name=f"Debt_Receipt_{selected_debt['id']}.txt", mime="text/plain")
            else:
                st.info("قم بإجراء عملية تسديد لعرض سند القبض هنا.")

# ----------------------------------------------------
# 4. قسم استرجاع المبيعات المطور
# ----------------------------------------------------
elif menu == "🔄 استرجاع المبيعات المطور":
    st.header("🔄 قسم إدارة المرتجعات والاسترجاع المتقدم")
    df_sales = get_sales_history()
    
    if df_sales.empty:
        st.info("💡 لا توجد عمليات بيع مسجلة حالياً في النظام.")
    else:
        col_search1, col_search2 = st.columns([2, 1])
        with col_search1:
            search_refund = st.text_input("🔍 بحث عن فاتورة لمرتجع (برقم الفاتورة، اسم الزبون، أو رقم الهاتف):")
        
        df_sales['date_dt'] = pd.to_datetime(df_sales['date'])
        
        if search_refund:
            df_matching_sales = df_sales[
                df_sales["id"].astype(str).str.contains(search_refund, case=False, na=False) |
                df_sales["customer_name"].str.contains(search_refund, case=False, na=False) |
                df_sales["customer_phone"].str.contains(search_refund, case=False, na=False) |
                df_sales["product_name"].str.contains(search_refund, case=False, na=False)
            ]
        else:
            df_matching_sales = df_sales

        st.subheader("📑 سجل الفواتير المتاحة بالكامل")
        
        invoices_summary = df_matching_sales.groupby("id").agg({
            "customer_name": "first",
            "customer_phone": "first",
            "payment_method": "first",
            "total_price": "sum",
            "quantity": "sum",
            "date": "first"
        }).reset_index().sort_values(by="id", ascending=False)

        st.dataframe(
            invoices_summary,
            column_config={
                "id": "رقم الفاتورة",
                "customer_name": "اسم الزبون",
                "customer_phone": "رقم الهاتف",
                "payment_method": "طريقة الدفع",
                "total_price": st.column_config.NumberColumn("إجمالي الفاتورة", format="%.2f د.أ"),
                "quantity": "إجمالي القطع",
                "date": "التاريخ والوقت"
            },
            use_container_width=True, hide_index=True
        )

        st.divider()
        st.subheader("🔍 معاينة الفاتورة الكاملة وإجراء المرتجع")
        
        if invoices_summary.empty:
            st.warning("⚠️ لا توجد فواتير تطابق البحث.")
        else:
            selected_inv_id = st.selectbox("🎯 اختر رقم الفاتورة لاستعراض كافة مشترياتها وتنفيذ الإرجاع:", invoices_summary["id"].tolist())
            invoice_items = df_sales[df_sales["id"] == selected_inv_id]
            inv_header = invoice_items.iloc[0]
            
            inv_date = inv_header["date_dt"]
            days_passed = (datetime.datetime.now() - inv_date).days
            is_overdue = days_passed > 14

            st.write("---")
            c_info1, c_info2, c_info3 = st.columns(3)
            c_info1.info(f"👤 الزبون: **{inv_header['customer_name']}** ({inv_header['customer_phone']})")
            c_info2.warning(f"💳 طريقة الدفع: **{inv_header['payment_method']}**")
            
            if is_overdue:
                c_info3.error(f"⏱️ تاريخ الفاتورة: **{inv_header['date']}** (تجاوزت 14 يوماً - تتطلب موافقة المدير)")
            else:
                c_info3.success(f"⏱️ تاريخ الفاتورة: **{inv_header['date']}** (ضمن المهلة المسموحة: {days_passed} يوم)")

            st.markdown("##### 🛒 المنتجات والمشتريات داخل الفاتورة المختارة:")
            st.dataframe(
                invoice_items[["product_name", "quantity", "discount", "total_price"]],
                column_config={
                    "product_name": "اسم المنتج",
                    "quantity": "الكمية المشتراة",
                    "discount": st.column_config.NumberColumn("الخصم المطبق", format="%.2f د.أ"),
                    "total_price": st.column_config.NumberColumn("الإجمالي الصافي", format="%.2f د.أ")
                },
                use_container_width=True, hide_index=True
            )

            st.divider()

            col_ref1, col_ref2 = st.columns([1.2, 1], gap="large")
            
            with col_ref1:
                st.subheader("⚙️ تفاصيل الاسترجاع")
                selected_prod_refund = st.selectbox("اختر المنتج المراد إرجاعه من الفاتورة:", invoice_items["product_name"].tolist())
                refund_item_row = invoice_items[invoice_items["product_name"] == selected_prod_refund].iloc[0]
                
                unit_price = refund_item_row["total_price"] / refund_item_row["quantity"] if refund_item_row["quantity"] > 0 else 0

                return_reason = st.selectbox("📌 سبب إرجاع المنتج:", [
                    "خطأ في الشراء / تغيير رأي العميل",
                    "بضاعة تالفة / عيب تصنيع",
                    "منتهي الصلاحية",
                    "عدم تطابق المواصفات"
                ])

                max_q_refund = int(refund_item_row['quantity'])
                qty_to_refund = st.number_input("حدد عدد القطع المراد إرجاعها:", min_value=1, max_value=max_q_refund, value=1)
                refund_cash_amount = qty_to_refund * unit_price
                is_full_refund = (qty_to_refund == max_q_refund)

                is_credit_sale = "آجل" in str(inv_header['payment_method'])
                if is_credit_sale:
                    st.info(f"💡 هذه الفاتورة مدفوعة بالأصل **(آجل / ذمم)**. سيتم **خصم مبلغ ({refund_cash_amount:.2f} د.أ)** تلقائياً من حساب الدين القائم على العميل.")
                else:
                    st.markdown(f"💵 **المبلغ المسترد للزبون نقداً:** <span style='color:#ef4444; font-size:20px; font-weight:bold;'>{refund_cash_amount:.2f} د.أ</span>", unsafe_allow_html=True)

                default_restock = False if ("تالفة" in return_reason or "الصلاحية" in return_reason) else True
                restock_choice = st.checkbox("🔄 إعادة القطع المسترجعة للمخزون؟", value=default_restock)

                admin_authorized = True
                if is_overdue or st.session_state["user_role"] != "Admin":
                    st.write("---")
                    st.warning("🔒 يلزم تأكيد وإدخال كلمة سر المدير (Admin) لإتمام العملية:")
                    admin_pass_input = st.text_input("كلمة سر المدير (Admin Password):", type="password", key="admin_refund_pass")
                    if admin_pass_input != "admin123":
                        admin_authorized = False

                if st.button("❌ تأكيد وتنفيذ عملية الإرجاع فوراً", type="primary", use_container_width=True):
                    if not admin_authorized:
                        st.error("❌ كلمة سر المدير غير صحيحة أو غير مدخلة! لا يمكن إتمام عملية الاسترجاع.")
                    else:
                        refund_sale_advanced(
                            sale_id=refund_item_row['id'],
                            product_name=refund_item_row['product_name'],
                            qty_to_refund=qty_to_refund,
                            refund_amount=refund_cash_amount,
                            return_to_stock=restock_choice,
                            is_full_refund=is_full_refund
                        )
                        
                        st.success(f"✅ تم إرجاع ({qty_to_refund}) قطعة من [{refund_item_row['product_name']}] بنجاح!")
                        
                        if is_credit_sale:
                            st.success("💳 تم تسوية المبلغ وخصمه من دين العميل بنجاح.")
                        if restock_choice:
                            st.info("📦 تم إعادة القطع إلى المخزن بنجاح.")
                        else:
                            st.warning("⚠️ لم يتم إعادة القطع للمخزون (تم تسجيلها كبضاعة تالفة/منتهية الصلاحية).")

                        now_ref_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        refund_receipt_text = f"""
========================================
         👑 متاجر المشاقبة 👑
       إيصال استرجاع مبيعات / مرتجع
========================================
التاريخ: {now_ref_str}
رقم الفاتورة الأصلية: #{selected_inv_id}
اسم الزبون: {inv_header['customer_name']}
رقم الهاتف: {inv_header['customer_phone']}
----------------------------------------
المنتج المسترجع: {refund_item_row['product_name']}
الكمية المسترجعة: {qty_to_refund} قطعة
سبب الإرجاع: {return_reason}
نوع التسوية المالية: {'خصم من الدين (آجل)' if is_credit_sale else 'استرداد نقدي'}
المبلغ المسترد: {refund_cash_amount:.2f} د.أ
حالة المخزون: {'تمت الإعادة للمخزن' if restock_choice else 'بضاعة تالفة / لم تُعد للمخزن'}
----------------------------------------
توقيع المسؤول: __________________
========================================
                  """
                        st.session_state["last_refund_receipt"] = refund_receipt_text
                        st.rerun()

            with col_ref2:
                st.subheader("📄 معاينة إيصال الإرجاع")
                if "last_refund_receipt" in st.session_state:
                    st.text_area("معاينة سند المرتجع:", st.session_state["last_refund_receipt"], height=320)
                    st.download_button("🖨️ تنزيل سند المرتجع (TXT)", data=st.session_state["last_refund_receipt"], file_name=f"Refund_Receipt_{selected_inv_id}.txt", mime="text/plain")
                else:
                    st.info("قم بإجراء عملية إرجاع لعرض المعاينة وطباعتها هنا.")

# ----------------------------------------------------
# 5. قسم إدارة المخزون المطور (تحديث شامل)
# ----------------------------------------------------
elif menu == "📦 إدارة المخزون المطور":
    st.header("📦 إدارة المخزون والمنتجات المتكاملة")
    
    tab_overview, tab_add, tab_edit_delete, tab_import_export, tab_barcode = st.tabs([
        "📋 جرد المخزون العام", 
        "➕ إضافة منتج جديد", 
        "✏️ تعديل / حذف منتج", 
        "📥 استيراد وتصدير (CSV)",
        "📊 مولد الباركود"
    ])
    
    # 1. جرد المخزون العام
    with tab_overview:
        df_p = get_products()
        if df_p.empty:
            st.info("💡 لا توجد منتجات بالمخزن حالياً.")
        else:
            st.subheader("📊 ملخص أحجام المخزون والماليات")
            total_items_count = len(df_p)
            total_stock_qty = df_p["stock"].sum()
            inventory_cost_value = (df_p["stock"] * df_p["cost_price"]).sum()
            inventory_sale_value = (df_p["stock"] * df_p["price"]).sum()
            expected_profit = inventory_sale_value - inventory_cost_value

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📦 عدد الأصناف", f"{total_items_count} صنف")
            k2.metric("🔢 مجموع القطع", f"{total_stock_qty} قطعة")
            k3.metric("💰 القيمة بسعر التكلفة", f"{inventory_cost_value:.2f} د.أ")
            k4.metric("📈 الأرباح المتوقعة", f"{expected_profit:.2f} د.أ")

            st.write("---")
            search_inv = st.text_input("🔍 بحث وتصفية السجل (بالاسم، التصنيف، المورد، أو الباركود):", key="search_inv_tab")
            if search_inv:
                filtered_df = df_p[
                    df_p["name"].str.contains(search_inv, case=False, na=False) |
                    df_p["category"].str.contains(search_inv, case=False, na=False) |
                    df_p["supplier"].str.contains(search_inv, case=False, na=False) |
                    df_p["barcode"].astype(str).str.contains(search_inv, case=False, na=False)
                ]
            else:
                filtered_df = df_p

            st.dataframe(
                filtered_df[[
                    "id", "barcode", "name", "category", "price", "cost_price", 
                    "stock", "min_alert", "supplier", "expiry_date"
                ]],
                column_config={
                    "id": "المُعرف",
                    "barcode": "الباركود/SKU",
                    "name": "اسم المنتج",
                    "category": "التصنيف",
                    "price": st.column_config.NumberColumn("سعر البيع", format="%.2f د.أ"),
                    "cost_price": st.column_config.NumberColumn("سعر التكلفة", format="%.2f د.أ"),
                    "stock": "الكمية المتاحة",
                    "min_alert": "حد الإنذار",
                    "supplier": "المورد",
                    "expiry_date": "تاريخ الصلاحية"
                },
                use_container_width=True, hide_index=True
            )

    # 2. إضافة منتج جديد
    with tab_add:
        st.subheader("➕ إضافة صنف جديد للمخزن")
        with st.form("add_product_form_adv", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                name = st.text_input("اسم المنتج *", placeholder="مثال: شوكولاتة جواهر 500غم")
                category = st.text_input("التصنيف / القسم", placeholder="مثال: حلويات / ألبان")
                price = st.number_input("سعر البيع للزبون (د.أ) *", min_value=0.0, format="%.2f")
                cost_price = st.number_input("سعر التكلفة / الشراء (د.أ)", min_value=0.0, format="%.2f")
                stock = st.number_input("الكمية الأولية بالمخزن *", min_value=0, step=1, value=10)
            
            with col_a2:
                barcode = st.text_input("الباروكود / SKU", value=f"629{datetime.datetime.now().strftime('%M%S%f')[:6]}")
                supplier = st.text_input("اسم المورد / الشركة", placeholder="مثال: شركة النبلاء للتوزيع")
                expiry_date = st.date_input("تاريخ انتهاء الصلاحية (اختياري)", value=datetime.date.today() + datetime.timedelta(days=365))
                min_alert = st.number_input("حد الإنذار للنقص الخاص بالمنتج", min_value=1, value=5)

            submit = st.form_submit_button("✨ حفظ وإضافة المنتج للمخزن", type="primary", use_container_width=True)
            if submit:
                if not name:
                    st.error("❌ يرجى إدخال اسم المنتج على الأقل.")
                else:
                    add_product(name, category, price, cost_price, stock, barcode, supplier, str(expiry_date), min_alert)
                    st.success(f"✅ تم إضافة المنتج [{name}] للمخزن بنجاح!")
                    st.rerun()

    # 3. تعديل أو حذف منتج
    with tab_edit_delete:
        df_products = get_products()
        if df_products.empty:
            st.info("لا توجد منتجات بالمخزن للتعديل عليها.")
        else:
            st.subheader("✏️ تعديل بيانات صنف موجود")
            prod_to_edit = st.selectbox("اختر المنتج المراد تعديله أو حذفه:", df_products["name"].tolist(), key="edit_select_adv")
            selected_row = df_products[df_products["name"] == prod_to_edit].iloc[0]
            
            with st.form("edit_prod_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    new_name = st.text_input("اسم المنتج", value=selected_row["name"])
                    new_cat = st.text_input("التصنيف", value=str(selected_row["category"]))
                    new_price = st.number_input("سعر البيع (د.أ)", value=float(selected_row["price"]))
                    new_cost = st.number_input("سعر التكلفة (د.أ)", value=float(selected_row["cost_price"]) if selected_row["cost_price"] else 0.0)
                    new_stock = st.number_input("الكمية المتوفرة بالمخزن", value=int(selected_row["stock"]))

                with e_col2:
                    new_barcode = st.text_input("الباركود / SKU", value=str(selected_row["barcode"]))
                    new_supplier = st.text_input("المورد", value=str(selected_row["supplier"]))
                    new_exp = st.text_input("تاريخ انتهاء الصلاحية", value=str(selected_row["expiry_date"]))
                    new_alert = st.number_input("حد أدنى للإنذار", value=int(selected_row["min_alert"]) if selected_row["min_alert"] else 5)

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    btn_update = st.form_submit_button("💾 حفظ التحديثات", type="primary", use_container_width=True)
                with col_btn2:
                    btn_delete = st.form_submit_button("❌ حذف المنتج نهائياً", use_container_width=True)

                if btn_update:
                    update_product(
                        selected_row["id"], new_name, new_cat, new_price, 
                        new_cost, new_stock, new_barcode, new_supplier, new_exp, new_alert
                    )
                    st.success("✅ تم تحديث بيانات المنتج بنجاح!")
                    st.rerun()

                if btn_delete:
                    delete_product(selected_row["id"])
                    st.success("✅ تم حذف المنتج نهائياً من قاعدة البيانات.")
                    st.rerun()

    # 4. استيراد وتصدير الشحنات (CSV / Excel)
    with tab_import_export:
        st.subheader("📥 استيراد وتصدير بيانات المخزون دفعة واحدة")
        col_imp, col_exp = st.columns(2, gap="large")

        with col_imp:
            st.markdown("##### 📤 استيراد شحنة جديدة من ملف CSV")
            uploaded_file = st.file_uploader("قم برفع ملف البيانات (.csv)", type=["csv"])
            if uploaded_file is not None:
                try:
                    import_df = pd.read_csv(uploaded_file)
                    st.write("معاينة البيانات المراد إدراجها:")
                    st.dataframe(import_df.head(), use_container_width=True)
                    
                    if st.button("✨ إدراج كافة الشحنة إلى المخزن الآن", type="primary"):
                        for _, r in import_df.iterrows():
                            add_product(
                                name=r.get("name", "منتج مستورد"),
                                category=r.get("category", "عام"),
                                price=float(r.get("price", 0.0)),
                                cost_price=float(r.get("cost_price", 0.0)),
                                stock=int(r.get("stock", 1)),
                                barcode=str(r.get("barcode", "-")),
                                supplier=str(r.get("supplier", "-")),
                                expiry_date=str(r.get("expiry_date", "-")),
                                min_alert=int(r.get("min_alert", 5))
                            )
                        st.success("✅ تم استيراد كافة المنتجات بنجاح إلى قاعدة البيانات!")
                        st.rerun()
                except Exception as ex:
                    st.error(f"❌ حدث خطأ أثناء قراءة الملف: {ex}")

        with col_exp:
            st.markdown("##### 📥 تصدير جرد المخزون الحالي")
            df_curr = get_products()
            if not df_curr.empty:
                csv_bytes = df_curr.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📊 تنزيل ملف المخزون الكامل (.csv)", 
                    data=csv_bytes, 
                    file_name=f"Full_Inventory_{datetime.date.today()}.csv", 
                    mime="text/csv", 
                    use_container_width=True
                )

    # 5. مولد ملصقات الباركود
    with tab_barcode:
        st.subheader("📊 مولد ملصقات الشفرة الخيطية والبارمود (Barcode Generator)")
        df_products = get_products()
        if not df_products.empty:
            b_prod = st.selectbox("اختر المنتج لتوليد باركوده:", df_products["name"].tolist(), key="select_barcode_prod")
            b_data = df_products[df_products["name"] == b_prod].iloc[0]

            st.write("---")
            bc_html = f"""
            <div style="border: 2px solid #f59e0b; padding: 15px; border-radius: 10px; width: 280px; text-align: center; background-color: #111827; margin: auto;">
                <h4 style="color: #f59e0b; margin: 0;">👑 متاجر المشاقبة</h4>
                <p style="color: #ffffff; font-weight: bold; margin: 5px 0;">{b_data['name']}</p>
                <div style="background-color: #ffffff; padding: 10px; margin: 10px 0; border-radius: 5px;">
                    <span style="font-family: 'Courier New', monospace; font-size: 24px; font-weight: bold; letter-spacing: 4px; color: #000000;">
                    |||| | ||||| | ||| ||
                    </span>
                    <br>
                    <span style="font-family: monospace; font-size: 14px; color: #000000;">{b_data['barcode']}</span>
                </div>
                <h3 style="color: #10b981; margin: 5px 0;">{b_data['price']:.2f} د.أ</h3>
            </div>
            """
            st.markdown(bc_html, unsafe_allow_html=True)

# ----------------------------------------------------
# 6. طباعة بطاقات الأسعار والملصقات المطور
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

        # تحديد أبعاد الكرت بناءً على الحجم
        card_width = "380px" if "كبير" in tag_size else "280px"
        font_size_price = "46px" if "كبير" in tag_size else "34px"

        st.divider()
        st.subheader("🖼️ معاينة البطاقة قبل الطباعة")

        # 1. القالب الذهبي الفاخر
        if "الذهبي" in tag_style:
            tag_html = f"""
            <div style="
                border: 2px solid #d97706; 
                background: linear-gradient(135deg, #111827 0%, #1f2937 100%); 
                padding: 18px; 
                border-radius: 16px; 
                width: {card_width}; 
                text-align: center; 
                box-shadow: 0 10px 25px rgba(245, 158, 11, 0.2); 
                margin: auto; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: white;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #374151; padding-bottom: 8px;">
                    <span style="color: #f59e0b; font-weight: bold; font-size: 14px;">👑 متاجر المشاقبة</span>
                    <span style="background-color: #d97706; color: black; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">جودة عالية</span>
                </div>
                <h2 style="color: #ffffff; margin: 12px 0 4px 0; font-size: 20px; font-weight: 700;">{prod_data['name']}</h2>
                <p style="color: #9ca3af; font-size: 12px; margin: 0 0 10px 0;">التصنيف: {prod_data['category']}</p>
                
                <div style="background: rgba(245, 158, 11, 0.1); border: 1px dashed #f59e0b; padding: 10px; border-radius: 12px; margin: 10px 0;">
                    <span style="color: #10b981; font-size: {font_size_price}; font-weight: 900;">{prod_data['price']:.2f}</span>
                    <span style="color: #10b981; font-size: 18px; font-weight: bold;"> د.أ</span>
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #6b7280; margin-top: 8px;">
                    <span>كود: {prod_data['barcode']}</span>
                    <span>المُعرف: #{prod_data['id']}</span>
                </div>
            </div>
            """

        # 2. قالب العروض والتخفيضات
        elif "العروض" in tag_style:
            tag_html = f"""
            <div style="
                border: 3px solid #ef4444; 
                background: #ffffff; 
                padding: 18px; 
                border-radius: 16px; 
                width: {card_width}; 
                text-align: center; 
                box-shadow: 0 10px 20px rgba(239, 68, 68, 0.2); 
                margin: auto; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #111827;
            ">
                <div style="background-color: #ef4444; color: white; font-weight: 900; font-size: 14px; padding: 4px 0; border-radius: 8px; margin-bottom: 10px; text-transform: uppercase;">
                    🔥 عرض خاص - SPECIAL OFFER 🔥
                </div>
                <h2 style="color: #111827; margin: 8px 0 2px 0; font-size: 20px; font-weight: 800;">{prod_data['name']}</h2>
                <p style="color: #6b7280; font-size: 12px; margin: 0 0 8px 0;">👑 متاجر المشاقبة</p>
                
                <div style="background-color: #fef2f2; border: 2px solid #fca5a5; padding: 8px; border-radius: 12px; margin: 8px 0;">
                    <span style="color: #dc2626; font-size: {font_size_price}; font-weight: 900;">{prod_data['price']:.2f}</span>
                    <span style="color: #dc2626; font-size: 18px; font-weight: bold;"> د.أ</span>
                </div>
                
                <div style="font-size: 11px; color: #9ca3af; margin-top: 6px;">
                    الباركود: {prod_data['barcode']}
                </div>
            </div>
            """

        # 3. القالب العصري البسيط
        else:
            tag_html = f"""
            <div style="
                border: 1px solid #e5e7eb; 
                background: #f9fafb; 
                padding: 18px; 
                border-radius: 12px; 
                width: {card_width}; 
                text-align: center; 
                margin: auto; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #111827;
            ">
                <h4 style="color: #4b5563; margin: 0 0 6px 0; font-size: 13px; font-weight: 600;">👑 متاجر المشاقبة</h4>
                <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 6px 0 12px 0;">
                <h2 style="color: #1f2937; margin: 4px 0; font-size: 19px; font-weight: 700;">{prod_data['name']}</h2>
                
                <h1 style="color: #059669; font-size: {font_size_price}; margin: 10px 0; font-weight: 800;">
                    {prod_data['price']:.2f} <span style="font-size:16px;">د.أ</span>
                </h1>
                
                <div style="background: #ffffff; padding: 4px; border: 1px solid #d1d5db; border-radius: 6px; display: inline-block; margin-top: 4px;">
                    <span style="font-family: monospace; font-size: 12px; color: #374151;">SKU: {prod_data['barcode']}</span>
                </div>
            </div>
            """

        # عرض المعاينة
        st.markdown(tag_html, unsafe_allow_html=True)
        
        st.write("---")
        
        # كود جاهز لفتح نافذة الطباعة فوراً
        print_code = f"""
        <html>
        <head>
            <title>طباعة بطاقة - {prod_data['name']}</title>
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
            file_name=f"PriceTag_{prod_data['id']}.html",
            mime="text/html",
            type="primary",
            use_container_width=True
        )
# ----------------------------------------------------
# 7. السجل والتقارير المتقدمة (نسخة عالمية BI)
# ----------------------------------------------------
elif menu == "📊 السجل والتقارير المتقدمة":
    st.header("📊 مركز التحليلات المالي وذكاء الأعمال (Business Intelligence)")
    
    df_sales = get_sales_history()
    df_products = get_products()
    
    if df_sales.empty:
        st.info("💡 لا توجد مبيعات مسجلة حتى الآن لعرض التقارير.")
    else:
        # تجهيز البيانات وربطها بسعر التكلفة لحساب الأرباح
        df_sales["date_dt"] = pd.to_datetime(df_sales["date"])
        
        # دمج سعر التكلفة من جدول المنتجات إذا توفر
        if not df_products.empty and "cost_price" in df_products.columns:
            df_merged = df_sales.merge(
                df_products[["name", "cost_price"]], 
                left_on="product_name", 
                right_on="name", 
                how="left"
            ).fillna({"cost_price": 0})
        else:
            df_merged = df_sales.copy()
            df_merged["cost_price"] = 0

        df_merged["total_cost"] = df_merged["cost_price"] * df_merged["quantity"]
        df_merged["net_profit"] = df_merged["total_price"] - df_merged["total_cost"]

        # --- شريط الفلاتر المتقدم ---
        st.subheader("🔍 خيارات الفلترة المتقدمة")
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            date_filter = st.selectbox("📅 الفترة الزمنية:", ["الكل", "اليوم", "آخر 7 أيام", "هذا الشهر", "نطاق تاريخ مخصص"])
        
        with f_col2:
            pay_filter = st.multiselect("💳 طريقة الدفع:", df_merged["payment_method"].dropna().unique().tolist(), default=df_merged["payment_method"].dropna().unique().tolist())
            
        with f_col3:
            search_prod_sales = st.text_input("🔍 فلترة باسم منتج أو زبون معين:")

        today = datetime.datetime.now().date()
        
        # تطبيق الفلترة حسب التاريخ
        if date_filter == "اليوم":
            df_filtered = df_merged[df_merged["date_dt"].dt.date == today]
        elif date_filter == "آخر 7 أيام":
            df_filtered = df_merged[df_merged["date_dt"].dt.date >= (today - datetime.timedelta(days=7))]
        elif date_filter == "هذا الشهر":
            df_filtered = df_merged[(df_merged["date_dt"].dt.month == today.month) & (df_merged["date_dt"].dt.year == today.year)]
        elif date_filter == "نطاق تاريخ مخصص":
            d_start = st.date_input("من تاريخ:", value=today - datetime.timedelta(days=30))
            d_end = st.date_input("إلى تاريخ:", value=today)
            df_filtered = df_merged[(df_merged["date_dt"].dt.date >= d_start) & (df_merged["date_dt"].dt.date <= d_end)]
        else:
            df_filtered = df_merged

        # تطبيق فلترة الطرق والبحث
        if pay_filter:
            df_filtered = df_filtered[df_filtered["payment_method"].isin(pay_filter)]
            
        if search_prod_sales:
            df_filtered = df_filtered[
                df_filtered["product_name"].str.contains(search_prod_sales, case=False, na=False) |
                df_filtered["customer_name"].str.contains(search_prod_sales, case=False, na=False)
            ]

        st.divider()

        # --- المؤشرات الرئيسية (KPIs) ---
        total_revenue = df_filtered["total_price"].sum()
        total_profit = df_filtered["net_profit"].sum()
        total_qty = int(df_filtered["quantity"].sum())
        total_orders = df_filtered["id"].nunique()
        avg_order_val = total_revenue / total_orders if total_orders > 0 else 0
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

        st.subheader("📈 أهم مؤشرات الأداء المالي (Global KPIs)")
        k1, k2, k3, k4, k5 = st.columns(5)
        
        k1.metric("💵 إجمالي المبيعات", f"{total_revenue:.2f} د.أ")
        k2.metric("🟢 صافي الأرباح", f"{total_profit:.2f} د.أ", delta=f"{profit_margin:.1f}% هامش ربح")
        k3.metric("🛒 عدد الفواتير", f"{total_orders} فاتورة")
        k4.metric("📊 متوسط الفاتورة (AOV)", f"{avg_order_val:.2f} د.أ")
        k5.metric("📦 القطع المباعة", f"{total_qty} قطعة")

        st.divider()

        # --- الرسم البياني ومخططات الأداء ---
        tab_charts, tab_top, tab_raw_data = st.tabs(["📈 الاتجاهات والذروة", "🏆 الأفضل أداءً والعملاء", "📋 جدول البيانات التفصيلي"])

        with tab_charts:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("📆 اتجاه المبيعات اليومية (Daily Sales Trend)")
                if not df_filtered.empty:
                    daily_sales = df_filtered.groupby(df_filtered["date_dt"].dt.date)["total_price"].sum()
                    st.line_chart(daily_sales)

            with col_chart2:
                st.subheader("⏰ المبيعات حسب ساعات اليوم (Peak Hours)")
                if not df_filtered.empty:
                    df_filtered["hour"] = df_filtered["date_dt"].dt.hour
                    hourly_sales = df_filtered.groupby("hour")["total_price"].sum()
                    st.bar_chart(hourly_sales)

            st.write("---")
            st.subheader("💳 توزيع المبيعات حسب طريقة الدفع")
            pay_dist = df_filtered.groupby("payment_method")["total_price"].sum()
            st.bar_chart(pay_dist)

        with tab_top:
            top_c1, top_c2 = st.columns(2)
            
            with top_c1:
                st.markdown("##### 🥇 المنتجات الأكثر تحقيقاً للأرباح الصافية")
                top_profits = df_filtered.groupby("product_name")["net_profit"].sum().sort_values(ascending=False).head(5)
                st.dataframe(top_profits, column_config={"net_profit": st.column_config.NumberColumn("صافي الربح", format="%.2f د.أ")})

            with top_c2:
                st.markdown("##### 👤 كبار العملاء الأكثر شراءً (VIP Customers)")
                top_customers = df_filtered.groupby(["customer_name", "customer_phone"])["total_price"].sum().sort_values(ascending=False).head(5).reset_index()
                st.dataframe(top_customers, column_config={
                    "customer_name": "اسم العمـيل",
                    "customer_phone": "الهاتف",
                    "total_price": st.column_config.NumberColumn("مجموع المشتريات", format="%.2f د.أ")
                }, hide_index=True)

        with tab_raw_data:
            st.subheader("📋 السجل التفصيلي المفلتر")
            
            disp_df = df_filtered[[
                "id", "date", "customer_name", "product_name", 
                "quantity", "total_price", "net_profit", "payment_method"
            ]].copy()
            
            st.dataframe(
                disp_df,
                column_config={
                    "id": "رقم الفاتورة",
                    "date": "التاريخ والوقت",
                    "customer_name": "الزبون",
                    "product_name": "المنتج",
                    "quantity": "الكمية",
                    "total_price": st.column_config.NumberColumn("الإجمالي الصافي", format="%.2f د.أ"),
                    "net_profit": st.column_config.NumberColumn("صافي الربح", format="%.2f د.أ"),
                    "payment_method": "طريقة الدفع"
                },
                use_container_width=True, hide_index=True
            )

            csv_export = disp_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 تصدير التقرير المالي الحالي إلى CSV/Excel", 
                data=csv_export, 
                file_name=f"Financial_Report_{datetime.date.today()}.csv", 
                mime="text/csv", 
                type="primary", 
                use_container_width=True
            )se_container_width=True)

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