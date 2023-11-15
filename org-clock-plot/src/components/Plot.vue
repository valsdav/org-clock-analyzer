<script >
import icicle from 'icicle-chart';
import * as d3 from 'd3';
import axios from 'axios';

export default {

  data(){
      return {"plot_data" : {}}
  },

    
  computed: {
      start() { return this.$route.query.start},
      end() { return this.$route.query.end}
  },

  mounted () {
      let query_options = "";
      // if(this.start != undefined && this.end!=undefined){
      //     query_options += "?start=" + this.start + "&end=" this.end;
      // }
            axios.get("http://127.0.0.1:5000/data?start=2023-10-23"+query_options).then(
          response => {
              console.log(response.data);
              const color = d3.scaleOrdinal(d3.schemePaired);
              this.plot_data = response.data;
              const myChart = icicle()
                    .label('name')
                    .size('value')
                    .excludeRoot(true)
                    .orientation('lr')
                    .tooltipContent((d, node) => `Time: <i>` + node.value.toFixed(2) + `</i> h<br/>Parent: <i>${node.data.relParent}%</i><br/>Total: <i>${node.data.relTot}%</i><br/>`)
                    .transitionDuration(400)
              .sort((a, b) => b.value - a.value)
                    .color((d, parent) => color(parent ? parent.data.name : null))
                    .data(this.plot_data)
              (this.$refs.plotbox);
          }
      );
      
  }
  }
  
</script>

<template>
  <div class="plot">
    <div ref="plotbox"/>
    
  </div>
</template>

<style scoped>

.icicle-viz text{
  font-size: 18px
}
</style>
