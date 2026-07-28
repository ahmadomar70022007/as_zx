import sqlite3
import pandas as pd
import streamlit as st
import io

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
            discount REAL DEFAULT 0,
            total_price REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # التحديث التلقائي: فحص ما إذا كان عمود الخصم موجوداً وإضافته إن لم يكن موجوداً
    cursor.execute("PRAGMA table_info(sales)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'discount' not in columns:
        cursor.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
        
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

def record_sale(product_id, product_name, quantity, discount_val, final_total):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, int(product_id)))
    cursor.execute("INSERT INTO sales (product_name, quantity, discount, total_price) VALUES (?, ?, ?, ?)",
                   (product_name, quantity, discount_val, final_total))
    sale_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sale_id

def refund_sale(sale_id, product_name, quantity):
    conn = get_connection()
    cursor = conn.cursor()
    # إعادة الكمية إلى جدول المنتجات
    cursor.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (quantity, product_name))
    # حذف السجل من جدول المبيعات
    cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    conn.commit()
    conn.close()

def get_sales_history():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM sales ORDER BY date DESC", conn)
    conn.close()
    return df

init_db()

# --- الهيدر الرئيسي والعلامة التجارية ---
st.markdown("<h2 style='text-align: center; color: #f59e0b;'>✨ بسم الله الرحمن الرحيم ✨</h2>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>👑 مَـتـاجِـر الـمُـشَـاقِـبَـة</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>AL-MASHAQBEH TRADING CO. - العلامة التجارية المسجلة ®</p>", unsafe_allow_html=True)
st.divider()

# القائمة الجانبية
menu = st.sidebar.radio("🔱 القائمة الرئيسية", [
    "🏪 كاشير المبيعات", 
    "🔄 استرجاع المبيعات", 
    "📦 إدارة المخزون", 
    "📊 سجل المبيعات والتقارير"
])

# ----------------------------------------------------
# 1. قسم كاشير المبيعات ونظام الفواتير والخصومات
# ----------------------------------------------------
if menu == "🏪 كاشير المبيعات":
    st.header("🛒 قسم المبيعات والخصومات")
    
    df_products = get_products()
    
    if df_products.empty:
        st.info("💡 لا توجد منتجات في المخزون حالياً. يرجى إضافة منتجات من قسم 'إدارة المخزون'.")
    else:
        col_action, col_display = st.columns([1.2, 1], gap="large")
        
        with col_action:
            st.subheader("🛍️ إعداد الفاتورة")
            
            product_list = df_products["name"].tolist()
            selected_product_name = st.selectbox("اختر المنتج:", options=product_list, key="cashier_select")
            
            prod_info = df_products[df_products["name"] == selected_product_name].iloc[0]
            
            m1, m2 = st.columns(2)
            m1.metric("💰 سعر القطعة", f"{prod_info['price']:.2f} د.أ")
            m2.metric("📦 المخزون المتاح", f"{prod_info['stock']} قطعة")
            
            if prod_info['stock'] <= 5 and prod_info['stock'] > 0:
                st.warning(f"⚠️ تنبيه: الكمية المتبقية قليلة جداً ({prod_info['stock']} فقط)!")
            elif prod_info['stock'] == 0:
                st.error("❌ هذا المنتج نافد من المخزون تماماً!")
            
            max_qty = int(prod_info['stock']) if prod_info['stock'] > 0 else 1
            qty = st.number_input("الكمية المطلوبة:", min_value=1, max_value=max_qty, value=1, disabled=(prod_info['stock'] == 0))
            
            # قسم نظام الخصومات والكوبونات
            st.write("---")
            st.subheader("🎟️ الخصومات والكوبونات")
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
                sale_id = record_sale(prod_info['id'], prod_info['name'], qty, discount_value, final_total)
                st.success(f"✅ تم تسجيل عملية البيع بنجاح! (رقم الفاتورة: #{sale_id})")
                
                # إنشاء النص الصريح للفاتورة للطباعة والتنزيل
                invoice_text = f"""
====================================
         👑 متاجر المشاقبة 👑
     AL-MASHAQBEH TRADING CO.
====================================
رقم الفاتورة: #{sale_id}
المنتج: {prod_info['name']}
الكمية: {qty}
سعر القطعة: {prod_info['price']:.2f} د.أ
------------------------------------
المجموع الفرعي: {subtotal:.2f} د.أ
الخصم: {discount_value:.2f} د.أ
الإجمالي النهائي: {final_total:.2f} د.أ
====================================
شكراً لتسوقكم معنا!
                """
                
                st.text_area("📄 معاينة الفاتورة للطباعة:", invoice_text, height=220)
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
# 2. قسم استرجاع / إرجاع المبيعات
# ----------------------------------------------------
elif menu == "🔄 استرجاع المبيعات":
    st.header("🔄 قسم استرجاع وإرجاع المبيعات")
    st.write("يمكنك البحث عن الفاتورة المباعة سابقاً وإتمام عملية الإرجاع لإعادة الكمية للمخزن.")
    
    df_sales = get_sales_history()
    if df_sales.empty:
        st.info("لا توجد عمليات بيع مسجلة لإرجاعها.")
    else:
        sale_to_refund = st.selectbox(
            "اختر رقم الفاتورة لإرجاعها:", 
            options=df_sales["id"].tolist(),
            format_func=lambda x: f"فاتورة #{x} - {df_sales[df_sales['id']==x]['product_name'].values[0]} (كمية: {df_sales[df_sales['id']==x]['quantity'].values[0]})"
        )
        
        selected_sale = df_sales[df_sales["id"] == sale_to_refund].iloc[0]
        
        st.warning(f"⚠️ تفاصيل العملية المراد إرجاعها:\n- المنتج: **{selected_sale['product_name']}**\n- الكمية: **{selected_sale['quantity']}**\n- المبلغ المسترد: **{selected_sale['total_price']:.2f} د.أ**")
        
        if st.button("❌ تأكيد استرجاع الفاتورة وإعادة للمخزون", type="primary"):
            refund_sale(selected_sale["id"], selected_sale["product_name"], int(selected_sale["quantity"]))
            st.success("✅ تم إرجاع المبلغ واستعادة الكمية إلى المخزون بنجاح!")
            st.rerun()

# ----------------------------------------------------
# 3. قسم إدارة المخزون
# ----------------------------------------------------
elif menu == "📦 إدارة المخزون":
    st.header("📦 إدارة المنتجات والمخزون")
    tab_add, tab_edit_delete = st.tabs(["➕ إضافة منتج جديد", "✏️ تعديل أو حذف منتج"])
    
    with tab_add:
        with st.form("add_product_form", clear_on_submit=True):
            name = st.text_input("اسم المنتج")
            category = st.text_input("التصنيف (مثال: إلكترونيات، رجالي...)")
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
                st.write("⚠️ **منطقة الحذف النهائي**")
                if st.button("❌ حذف هذا المنتج نهائياً", type="primary", key="btn_delete", use_container_width=True):
                    delete_product(selected_row["id"])
                    st.success("تم حذف المنتج نهائياً!")
                    st.rerun()

    st.divider()
    st.subheader("📋 قائمة المخزون الحالية")
    st.dataframe(get_products(), use_container_width=True)

# ----------------------------------------------------
# 4. قسم سجل المبيعات وتصدير التقارير (Excel / CSV)
# ----------------------------------------------------
elif menu == "📊 سجل المبيعات والتقارير":
    st.header("📊 سجل العمليات والتقارير المالية")
    df_sales = get_sales_history()
    
    if df_sales.empty:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")
    else:
        total_revenue = df_sales["total_price"].sum()
        total_items_sold = df_sales["quantity"].sum()
        total_discounts = df_sales["discount"].sum() if "discount" in df_sales.columns else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric(label="إجمالي صافي الأرباح/المبيعات", value=f"{total_revenue:.2f} د.أ")
        m2.metric(label="إجمالي القطع المباعة", value=f"{int(total_items_sold)} قطعة")
        m3.metric(label="إجمالي الخصومات الممنوحة", value=f"{total_discounts:.2f} د.أ")
        
        st.divider()
        st.subheader("📥 تصدير التقارير المالية")
        
        col_excel, col_csv = st.columns(2)
        
        # تصدير ملف Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_sales.to_excel(writer, index=False, sheet_name='Sales_Report')
        buffer.seek(0)
        
        with col_excel:
            st.download_button(
                label="📊 تصدير السجل كملف Excel (.xlsx)",
                data=buffer,
                file_name="Sales_Report_Mashaqa.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        # تصدير ملف CSV
        csv_data = df_sales.to_csv(index=False).encode('utf-8-sig')
        with col_csv:
            st.download_button(
                label="📄 تصدير السجل كملف CSV (.csv)",
                data=csv_data,
                file_name="Sales_Report_Mashaqa.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        st.divider()
        st.subheader("📋 جدول الفواتير والسجلات")
        st.dataframe(df_sales, use_container_width=True)