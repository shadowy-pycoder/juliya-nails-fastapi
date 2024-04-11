<template>
  <div class="home">
    <img alt="Vue logo" src="../assets/logo.png">
    <JuliyaNails msg="Welcome to Your Vue.js App"/>
  </div>
</template>

<script>
// @ is an alias to /src
import JuliyaNails from '@/components/JuliyaNails.vue'

export default {
  name: 'HomeView',
  components: {
    JuliyaNails
  }
}
</script>
