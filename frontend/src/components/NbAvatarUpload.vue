<template>
  <view
    class="nb-avatar-upload"
    :class="{ disabled: disabled || uploading }"
    :style="rootStyle"
    @click="handleTap"
  >
    <image class="nb-avatar-img" :src="safeSrc" mode="aspectFill" />

    <view class="nb-avatar-badge" :class="{ uploading }" aria-hidden="true">
      <text v-if="uploading" class="nb-avatar-badge-text">上传中</text>
      <text v-else class="nb-avatar-badge-text">更换</text>
    </view>
  </view>
</template>

<script>
import api, { NB_AUTH_REDIRECT_TOAST_TITLE } from '@/utils/api'

export default {
  name: 'NbAvatarUpload',
  props: {
    src: { type: String, default: '' },
    uploadUrl: { type: String, default: '' },
    size: { type: Number, default: 72 },
    radius: { type: Number, default: 22 },
    disabled: { type: Boolean, default: false },
  },
  emits: ['uploaded'],
  data() {
    return {
      uploading: false,
    }
  },
  computed: {
    safeSrc() {
      const s = String(this.src || '').trim()
      return s || '/static/default-avatar.png'
    },
    rootStyle() {
      const size = Math.max(28, Number(this.size || 0))
      const r = Math.max(0, Number(this.radius || 0))
      return {
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: `${r}px`,
      }
    },
  },
  methods: {
    async handleTap() {
      if (this.disabled || this.uploading) return
      const uploadUrl = String(this.uploadUrl || '').trim()
      if (!uploadUrl) return

      this.uploading = true
      try {
        const img = await new Promise((resolve, reject) => {
          uni.chooseImage({
            count: 1,
            sizeType: ['compressed'],
            sourceType: ['album', 'camera'],
            success: resolve,
            fail: reject,
          })
        })

        const rawPath = (img && img.tempFilePaths && img.tempFilePaths[0]) ? String(img.tempFilePaths[0]) : ''
        if (!rawPath) return

        let path = rawPath
        try {
          const compressed = await new Promise((resolve, reject) => {
            uni.compressImage({
              src: rawPath,
              quality: 80,
              success: resolve,
              fail: reject,
            })
          })
          const p = compressed?.tempFilePath || compressed?.tempFilePaths?.[0]
          if (p) path = String(p)
        } catch {}

        const res = await api.upload(uploadUrl, path, { name: 'file' })
        const url = String(res?.url || '').trim()
        if (!url) throw new Error('上传失败：未返回URL')
        this.$emit('uploaded', url)
      } catch (e) {
        const msg = e?.message || '操作失败'
        if (msg === NB_AUTH_REDIRECT_TOAST_TITLE) return
        if (msg && msg !== 'chooseImage:fail cancel') {
          uni.showToast({ title: msg, icon: 'none' })
        }
      } finally {
        this.uploading = false
      }
    },
  },
}
</script>

<style scoped>
.nb-avatar-upload {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
  box-sizing: border-box;
  user-select: none;
}

.nb-avatar-upload:active:not(.disabled) {
  transform: scale(0.995);
}

.nb-avatar-upload.disabled {
  opacity: 0.78;
}

.nb-avatar-img {
  width: 100%;
  height: 100%;
}

.nb-avatar-badge {
  position: absolute;
  right: 8px;
  bottom: 8px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.68);
  background: rgba(27, 26, 23, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(10px);
  box-sizing: border-box;
}

.nb-avatar-badge.uploading {
  background: rgba(27, 26, 23, 0.58);
}

.nb-avatar-badge-text {
  font-size: 11px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.92);
  line-height: 1;
  white-space: nowrap;
}
</style>

