export default {
    message: {
        pages: {
            property: {
                buttons: {
                    view: 'ดู',
                    edit: 'แก้ไข',
                    delete: 'ลบ',
                },
                table: {
                    columns: {
                        index: 'ลำดับ',
                        name: 'ชื่อห้อง',
                        rentAmount: 'ค่าเช่า',
                        remindDay: 'วันแจ้งเตือน',
                        payPeriod: 'รอบชำระ',
                        rentStart: 'วันที่เริ่มเช่า',
                        rentEnd: 'วันที่สิ้นสุด',
                        groupId: 'Line Group ID',
                        groupSize: 'จำนวนคนในกลุ่ม',
                        lineBot: 'LineBot',
                        owner: 'ผู้รับผิดชอบ',
                        calendarIn: 'เขียนปฏิทิน',
                        annualNotify: 'แจ้งเตือนรายปี',
                        memo: 'หมายเหตุ',
                        event01: 'Event ID 01',
                        event02: 'Event ID 02',
                    },
                },
                validation: {
                    nameRequired: 'กรุณากรอกชื่อห้อง',
                    remindDayRequired: 'กรุณากรอกวันแจ้งเตือน (1-31)',
                    groupSizeRequired: 'กรุณากรอกจำนวนคนในกลุ่ม',
                },
                period: {
                    monthly: 'รายเดือน',
                    quarterly: 'รายไตรมาส',
                },
                card: {
                    memo: 'หมายเหตุ',
                    expired: 'หมดอายุ',
                },
            },
        },
    },
};
