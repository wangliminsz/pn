export default {
    message: {
        pages: {
            tenant: {
                buttons: {
                    edit: 'แก้ไข',
                    delete: 'ลบ',
                },
                table: {
                    columns: {
                        index: 'ลำดับ',
                        name: 'ชื่อบริษัท',
                        tenantCode: 'รหัสผู้เช่า',
                        contact: 'ผู้ติดต่อ',
                        phone: 'เบอร์โทร',
                        plan: 'ประเภทลูกค้า',
                        status: 'สถานะ',
                        expire: 'วันหมดอายุ',
                        calendarId: 'Google',
                        signName: 'ชื่อลงท้าย',
                        remark: 'หมายเหตุ',
                    },
                },
                validation: {
                    nameRequired: 'กรุณากรอกชื่อบริษัท',
                    codeRequired: 'กรุณากรอกรหัสผู้เช่า',
                    planRequired: 'กรุณาเลือกประเภทลูกค้า',
                },
                plan: {
                    trial: 'ลูกค้าทดลอง',
                    paid: 'ลูกค้าจริง',
                },
            },
        },
    },
};
