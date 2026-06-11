<script setup lang="ts">
// A collapsed detail section whose summary carries a one-line takeaway (a pill,
// passed via the #takeaway slot) and whose body is the default slot.
defineProps<{ title: string }>();
</script>

<template>
  <details>
    <summary>
      <span class="st">{{ title }}</span>
      <slot name="takeaway" />
      <span class="chev">›</span>
    </summary>
    <div class="sbody"><slot /></div>
  </details>
</template>
