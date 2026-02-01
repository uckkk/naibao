// 用户头像库
// 默认头像列表
export const defaultAvatars = [
  {
    id: 'avatar_1',
    name: '可爱女孩',
    url: '/static/avatars/avatar_1.png',
    description: '双马尾女孩，带有花朵发夹'
  },
  {
    id: 'avatar_2',
    name: '小老虎',
    url: '/static/avatars/avatar_2.png',
    description: '可爱的卡通老虎幼崽'
  },
  {
    id: 'avatar_3',
    name: '小猪',
    url: '/static/avatars/avatar_3.png',
    description: '戴着花朵头巾的小猪，头顶有小鱼'
  },
  {
    id: 'avatar_4',
    name: '粉色女孩',
    url: '/static/avatars/avatar_4.png',
    description: '动漫风格女孩，粉色头带'
  },
  {
    id: 'avatar_5',
    name: '小佛像1',
    url: '/static/avatars/avatar_5.png',
    description: 'Q版小佛像，闭眼微笑'
  },
  {
    id: 'avatar_6',
    name: '小佛像2',
    url: '/static/avatars/avatar_6.png',
    description: '小佛像，手指向上'
  }
]

// 获取随机头像
export function getRandomAvatar() {
  const randomIndex = Math.floor(Math.random() * defaultAvatars.length)
  return defaultAvatars[randomIndex]
}

// 根据ID获取头像
export function getAvatarById(id) {
  return defaultAvatars.find(avatar => avatar.id === id) || defaultAvatars[0]
}

// 获取所有头像
export function getAllAvatars() {
  return defaultAvatars
}


