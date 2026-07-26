import sqlite3
import pandas as pd
import streamlit as st

# 1. تهيئة الصفحة
st.set_page_config(
    page_title="المشاقبة - نظام إدارة المبيعات والمخزون",
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
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
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

def record_sale(product_id, product_name, quantity, price):
    conn = get_connection()
    cursor = conn.cursor()
    total = quantity * price
    cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, int(product_id)))
    cursor.execute("INSERT INTO sales (product_name, quantity, total_price) VALUES (?, ?, ?)",
                   (product_name, quantity, total))
    conn.commit()
    conn.close()

def get_sales_history():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM sales ORDER BY date DESC", conn)
    conn.close()
    return df

# تهيئة قاعدة البيانات
init_db()

# --- الهيدر والعلامة التجارية ---
st.markdown("<h2 style='text-align: center; color: #f59e0b;'>✨ بسم الله الرحمن الرحيم ✨</h2>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>👑 مَـتـاجِـر الجامعه الهاشمية</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>AL-MASHAQBEH TRADING CO. - العلامة التجارية المسجلة ®</p>", unsafe_allow_html=True)
st.divider()

# القائمة الجانبية
menu = st.sidebar.radio("🔱 القائمة الرئيسية", ["🏪 كاشير المبيعات", "📦 إدارة المخزون", "📊 سجل المبيعات"])

# ----------------------------------------------------
# 1. قسم كاشير المبيعات
# ----------------------------------------------------
if menu == "🏪 كاشير المبيعات":
    st.header("🛒 قسم المبيعات والكاشير")
    
    df_products = get_products()
    
    if df_products.empty:
        st.info("💡 لا توجد منتجات في المخزون حالياً. يرجى إضافة منتجات من قسم 'إدارة المخزون'.")
    else:
        col_action, col_display = st.columns([1.1, 1], gap="large")
        
        with col_action:
            st.subheader("🛍️ اختر المنتج المطلوب")
            
            product_list = df_products["name"].tolist()
            
            selected_product_name = st.radio(
                "المنتجات المتاحة:",
                options=product_list,
                horizontal=True,
                key="cashier_radio"
            )
            
            if not selected_product_name:
                selected_product_name = product_list[0]
            
            prod_info = df_products[df_products["name"] == selected_product_name].iloc[0]
            
            st.write("---")
            st.subheader(f"🏷️ تفاصيل: {selected_product_name}")
            
            m1, m2 = st.columns(2)
            m1.metric("💰 سعر القطعة", f"{prod_info['price']:.2f} د.أ")
            m2.metric("📦 المخزون المتاح", f"{prod_info['stock']} قطعة")
            
            if prod_info['stock'] <= 5 and prod_info['stock'] > 0:
                st.warning(f"⚠️ تنبيه: الكمية المتبقية قليلة جداً ({prod_info['stock']} فقط)!")
            elif prod_info['stock'] == 0:
                st.error("❌ هذا المنتج نافد من المخزون تماماً!")
            
            max_qty = int(prod_info['stock']) if prod_info['stock'] > 0 else 1
            qty = st.number_input(
                "الكمية المطلوبة:", 
                min_value=1, 
                max_value=max_qty, 
                value=1,
                disabled=(prod_info['stock'] == 0),
                key="sale_qty_input"
            )
            
            total_amount = qty * prod_info['price']
            st.markdown(f"### 💵 إجمالي الفاتورة: **{total_amount:.2f} د.أ**")
            
            if st.button("✨ إتمام عملية البيع الآن", use_container_width=True, type="primary", disabled=(prod_info['stock'] == 0)):
                record_sale(prod_info['id'], prod_info['name'], qty, prod_info['price'])
                st.toast(f"✅ تم بيع {qty} من ({prod_info['name']}) بنجاح!", icon="🎉")
                st.rerun()

        with col_display:
            st.subheader("📋 قائمة المنتجات الحالية")
            
            search_query = st.text_input("🔍 بحث سريع عن منتج...", "", key="cashier_search")
            
            if search_query:
                filtered_df = df_products[df_products["name"].str.contains(search_query, case=False, na=False)]
            else:
                filtered_df = df_products

            st.dataframe(
                filtered_df[["id", "name", "price", "stock"]],
                column_config={
                    "id": "المُعرّف",
                    "name": "اسم المنتج",
                    "price": st.column_config.NumberColumn("السعر (د.أ)", format="%.2f د.أ"),
                    "stock": st.column_config.NumberColumn("الكمية المتاحة"),
                },
                use_container_width=True,
                hide_index=True
            )

# ----------------------------------------------------
# 2. قسم إدارة المخزون
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
                else:
                    st.warning("يرجى إدخال اسم المنتج.")

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
                st.write("⚠️ **منطقة الحذف**")
                if st.button("❌ حذف هذا المنتج نهائياً", type="primary", key="btn_delete", use_container_width=True):
                    delete_product(selected_row["id"])
                    st.success("تم حذف المنتج نهائياً!")
                    st.rerun()

    st.divider()
    st.subheader("📋 قائمة المخزون الحالية")
    st.dataframe(get_products(), use_container_width=True)

# ----------------------------------------------------
# 3. قسم سجل المبيعات
# ----------------------------------------------------
elif menu == "📊 سجل المبيعات":
    st.header("📊 سجل العمليات والتقارير المالية")
    df_sales = get_sales_history()
    
    if df_sales.empty:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
    else:
        total_revenue = df_sales["total_price"].sum()
        total_items_sold = df_sales["quantity"].sum()
        
        m1, m2 = st.columns(2)
        m1.metric(label="إجمالي المبيعات", value=f"{total_revenue:.2f} د.أ")
        m2.metric(label="إجمالي القطع المباعة", value=f"{int(total_items_sold)} قطعة")
        
        st.divider()
        st.dataframe(df_sales, use_container_width=True)