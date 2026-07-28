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
    
    # 1. إرجاع الكمية للمخزون إذا اختار المستخدم ذلك
    if return_to_stock:
        cursor.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (qty_to_refund, product_name))
    
    # 2. معالجة الفاتورة (إلغاء كامل أم تحديث جزئي)
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
        "📦 إدارة المخزون", 
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
            search_q = st.text_input("🔍 بحث سريع عن منتج بالاسم أو التصنيف...", key="pos_search")
            if search_q:
                filtered_prods = df_products[df_products["name"].str.contains(search_q, case=False, na=False) | df_products["category"].str.contains(search_q, case=False, na=False)]
            else:
                filtered_prods = df_products
                
            st.write("---")
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
            st.dataframe(filtered_prods[["id", "name", "category", "price", "stock"]], use_container_width=True, hide_index=True)

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
        col_ctrl1, col_ctrl2 = st.columns([2, 1])
        with col_ctrl1:
            threshold = st.slider("⚙️ حدد الكمية الحرجة للتنبيه (الحد الأدنى):", min_value=1, max_value=30, value=5)
        
        out_of_stock = df_products[df_products["stock"] == 0]
        low_stock = df_products[(df_products["stock"] > 0) & (df_products["stock"] <= threshold)]
        all_alert_products = df_products[df_products["stock"] <= threshold]

        ind1, ind2, ind3 = st.columns(3)
        ind1.metric("🔴 منتجات نافدة تماماً", f"{len(out_of_stock)} منتج", delta_color="inverse")
        ind2.metric("🟡 منتجات منخفضة", f"{len(low_stock)} منتج", delta_color="off")
        ind3.metric("📦 مجموع المنتجات للتزويد", f"{len(all_alert_products)} منتج")

        st.divider()

        if all_alert_products.empty:
            st.balloons()
            st.success("🎉 ممتاز جداً! جميع المنتجات في المخزن متوفرة بكميات كافية وأعلى من حد التنبيه.")
        else:
            if not out_of_stock.empty:
                st.error("🚨 **منتجات نافدة تماماً من المخزن (0 قطعة):**")
                st.dataframe(out_of_stock[["id", "name", "category", "price", "stock"]], use_container_width=True, hide_index=True)
                st.write("---")

            if not low_stock.empty:
                st.warning(f"⚠️ **منتجات أوشكت على النفاد (تتطلب طلبية جديدة):**")
                st.dataframe(low_stock[["id", "name", "category", "price", "stock"]], use_container_width=True, hide_index=True)
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
            reorder_csv = all_alert_products[["id", "name", "category", "stock"]].to_csv(index=False).encode('utf-8-sig')
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
# 4. قسم استرجاع المبيعات المطور المطور
# ----------------------------------------------------
elif menu == "🔄 استرجاع المبيعات المطور":
    st.header("🔄 قسم إدارة المرتجعات والاسترجاع المتقدم")
    df_sales = get_sales_history()
    
    if df_sales.empty:
        st.info("💡 لا توجد عمليات بيع مسجلة حالياً في النظام.")
    else:
        # البحث والفلترة
        col_search1, col_search2 = st.columns([2, 1])
        with col_search1:
            search_refund = st.text_input("🔍 بحث عن فاتورة لمرتجع (برقم الفاتورة، اسم الزبون، المنتج أو الهاتف):")
        
        if search_refund:
            df_filtered_sales = df_sales[
                df_sales["id"].astype(str).str.contains(search_refund, case=False, na=False) |
                df_sales["customer_name"].str.contains(search_refund, case=False, na=False) |
                df_sales["product_name"].str.contains(search_refund, case=False, na=False) |
                df_sales["customer_phone"].str.contains(search_refund, case=False, na=False)
            ]
        else:
            df_filtered_sales = df_sales

        st.subheader("📋 سجل الفواتير المتاحة للاسترجاع")
        st.dataframe(
            df_filtered_sales[["id", "customer_name", "customer_phone", "product_name", "quantity", "total_price", "payment_method", "date"]],
            column_config={
                "id": "رقم الفاتورة",
                "customer_name": "العميل",
                "customer_phone": "الهاتف",
                "product_name": "المنتج",
                "quantity": "الكمية المباعة",
                "total_price": st.column_config.NumberColumn("المبلغ الإجمالي", format="%.2f د.أ"),
                "payment_method": "طريقة الدفع",
                "date": "التاريخ"
            },
            use_container_width=True, hide_index=True
        )

        st.divider()

        # نافذة تنفيذ الإرجاع
        st.subheader("⚙️ إجراء وتنفيذ عملية الإرجاع")
        
        if df_filtered_sales.empty:
            st.warning("⚠️ لا توجد فواتير تطابق بحثك.")
        else:
            col_ref1, col_ref2 = st.columns([1.2, 1], gap="large")
            
            with col_ref1:
                selected_refund_id = st.selectbox("اختر رقم الفاتورة المراد إرجاعها:", df_filtered_sales["id"].tolist())
                refund_item = df_filtered_sales[df_filtered_sales["id"] == selected_refund_id].iloc[0]
                
                unit_price = refund_item["total_price"] / refund_item["quantity"] if refund_item["quantity"] > 0 else 0
                
                st.info(f"👤 الزبون: **{refund_item['customer_name']}** | 📱 الهاتف: **{refund_item['customer_phone']}**")
                st.warning(f"📦 المنتج: **{refund_item['product_name']}** | الكمية المباعة أصلياً: **{refund_item['quantity']} قطعة**")
                st.markdown(f"💰 السعر الإجمالي: **{refund_item['total_price']:.2f} د.أ** (سعر القطعة الصافي: **{unit_price:.2f} د.أ**)")

                refund_type = st.radio("نوع الاسترجاع:", ["استرجاع كلي (الفاتورة كاملة)", "استرجاع جزئي (بعض القطع)"], horizontal=True)
                
                if refund_type == "استرجاع جزئي (بعض القطع)":
                    max_q_refund = int(refund_item['quantity'])
                    qty_to_refund = st.number_input("حدد عدد القطع المراد إرجاعها:", min_value=1, max_value=max_q_refund, value=1)
                    refund_cash_amount = qty_to_refund * unit_price
                    is_full_refund = (qty_to_refund == max_q_refund)
                else:
                    qty_to_refund = int(refund_item['quantity'])
                    refund_cash_amount = float(refund_item['total_price'])
                    is_full_refund = True

                st.markdown(f"💵 **المبلغ المطلوب إرجاعه للزبون:** <span style='color:#ef4444; font-size:22px; font-weight:bold;'>{refund_cash_amount:.2f} د.أ</span>", unsafe_allow_html=True)

                restock_choice = st.checkbox("🔄 إعادة القطع المسترجعة للمخزون تلقائياً؟", value=True, help="الغي التحديد إذا كانت السلعة تالفة ولا تصلح للبيع مجدداً.")

                if st.button("❌ تأكيد وتنفيذ عملية الإرجاع فوراً", type="primary", use_container_width=True):
                    refund_sale_advanced(
                        sale_id=refund_item['id'],
                        product_name=refund_item['product_name'],
                        qty_to_refund=qty_to_refund,
                        refund_amount=refund_cash_amount,
                        return_to_stock=restock_choice,
                        is_full_refund=is_full_refund
                    )
                    
                    st.success(f"✅ تم إرجاع ({qty_to_refund}) قطعة من [{refund_item['product_name']}] بنجاح!")
                    if restock_choice:
                        st.info("📦 تم إعادة القطع إلى المخزن بنجاح.")
                    else:
                        st.warning("⚠️ لم يتم إضافة القطع للمخزون (تم احتسابها كتالفة).")

                    # إعداد إيصال المرتجع
                    now_ref_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    refund_receipt_text = f"""
========================================
         👑 متاجر المشاقبة 👑
       إيصال استرجاع مبيعات / مرتجع
========================================
التاريخ: {now_ref_str}
رقم الفاتورة الأصلية: #{refund_item['id']}
اسم الزبون: {refund_item['customer_name']}
----------------------------------------
المنتج المسترجع: {refund_item['product_name']}
الكمية المسترجعة: {qty_to_refund} قطعة
المبلغ المسترد للزبون: {refund_cash_amount:.2f} د.أ
حالة المخزون: {'تمت الإعادة للمخزن' if restock_choice else 'بضاعة تالفة'}
----------------------------------------
توقيع المسؤول: __________________
========================================
                  """
                    st.session_state["last_refund_receipt"] = refund_receipt_text
                    st.rerun()

            with col_ref2:
                st.subheader("📄 معاينة إيصال الإرجاع")
                if "last_refund_receipt" in st.session_state:
                    st.text_area("معاينة الإيصال:", st.session_state["last_refund_receipt"], height=270)
                    st.download_button("🖨️ تنزيل سند المرتجع (TXT)", data=st.session_state["last_refund_receipt"], file_name=f"Refund_Receipt_{selected_refund_id}.txt", mime="text/plain")
                else:
                    st.info("قم بإجراء عملية إرجاع لعرض المعاينة وطباعتها هنا.")

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