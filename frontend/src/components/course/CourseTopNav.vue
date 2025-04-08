<template>
  <div class="flex items-center justify-between w-full px-4 py-2 bg-white shadow">
    <div class="flex items-center">
      <button
        class="p-1 mr-2 text-slate-700 hover:text-slate-900 transition-colors"
        @click="$emit('goBack')"
      >
        <span class="material-symbols-rounded text-xl">arrow_back</span>
      </button>
      <div v-if="course" class="flex flex-col">
        <h2 class="text-sm font-semibold text-slate-800">{{ course.title }}</h2>
        <p v-if="currentLecture" class="text-xs text-slate-500">{{ currentLecture.title }}</p>
      </div>
    </div>
    <div class="flex-1 mx-4 max-w-md" v-if="progress">
      <div class="w-full bg-gray-200 rounded-full h-2">
        <div
          class="bg-maroon-600 h-2 rounded-full"
          :style="{ width: `${progress}%` }"
        ></div>
      </div>
    </div>
    <div class="flex items-center space-x-2">
      <button
        class="p-1 rounded hover:bg-gray-100 transition-colors"
        :class="{
          'text-maroon-600': isBookmarked,
          'text-maroon-500 hover:text-maroon-600': !isBookmarked,
        }"
        @click="$emit('toggleBookmark')"
        title="Bookmark this lecture"
      >
        <span 
          class="material-symbols-rounded icon-maroon"
          :class="{'material-symbols-filled': isBookmarked}"
        >
          bookmark
        </span>
      </button>
      <button
        class="p-1 rounded hover:bg-gray-100 transition-colors text-maroon-500 hover:text-maroon-600"
        @click="$emit('toggleNotes')"
        title="Show/hide notes"
      >
        <span class="material-symbols-rounded icon-maroon">edit_note</span>
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  course: Object,
  currentLecture: {
    type: Object,
    default: null
  },
  progress: Number,
  isBookmarked: Boolean,
})

defineEmits(['goBack', 'toggleBookmark', 'toggleNotes'])
</script>

<style scoped>
.material-symbols-rounded {
  font-size: 24px;
}
</style>
