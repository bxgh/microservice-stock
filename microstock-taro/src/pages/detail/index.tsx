import { View, Text } from '@tarojs/components'
import { useLoad } from '@tarojs/taro'

export default function Detail() {
    useLoad(() => {
        console.log('Detail Page loaded.')
    })

    return (
        <View className='detail'>
            <Text>Stock Detail Placeholder</Text>
        </View>
    )
}
