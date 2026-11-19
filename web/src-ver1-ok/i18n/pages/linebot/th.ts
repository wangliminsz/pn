export default {
    message: {
        pages: {
            linebot: {
                buttons: {
                    view: 'ดู',
                    edit: 'แก้ไข',
                    delete: 'ลบ',
                },
                table: {
                    columns: {
                        index: 'ลำดับ',
                        name: 'ชื่อ Bot',
                        botCode: 'รหัส Bot',
                        channelId: 'Channel ID',
                        basicId: 'Bot basic ID',
                        botUserId: 'Bot User Id',
                        tenant: 'ผู้เช่าที่ถือครอง',
                        channelSecret: 'Channel Secret',
                        channelAccessToken: 'Channel Access Token',
                        isDefault: 'Bot เริ่มต้น',
                        isActive: 'เปิดใช้งาน',
                        monthlyQuota: 'โควต้ารายเดือน',
                    },
                    placeholder: {
                        monthlyQuota: 'เว้นว่างใช้ค่ากลาง',
                    },
                },
                validation: {
                    nameRequired: 'กรุณากรอกชื่อ Bot',
                    botCodeRequired: 'กรุณากรอกรหัส Bot',
                },
            },
        },
    },
};
