import { View, Text } from '@tarojs/components'
import './index.scss'

export default function Index() {
    return (
        <View style={{ padding: '20px', background: '#fff', minHeight: '100vh' }}>
            <Text style={{ fontSize: '24px', color: '#333' }}>测试页面</Text>
            <Text style={{ fontSize: '16px', color: '#666', marginTop: '10px' }}>如果您能看到这段文字，说明 Taro 渲染正常</Text>
            <View style={{ marginTop: '20px', padding: '10px', background: '#f0f0f0' }}>
                <Text>这是一个灰色背景的测试区域</Text>
            </View>
        </View>
    )
}
