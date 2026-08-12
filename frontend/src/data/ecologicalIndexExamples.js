// 生态环境指数计算示例数据

// 生态环境结构指数示例数据
export const structureIndexExamples = [
  {
    name: '天水市秦州区',
    description: '城市建成区生态环境结构评估',
    params: {
      fragmentation: 1.2,
      cohesion: 75.5,
      diversity: 2.1,
      vulnerability: 35.2
    },
    expectedScore: 78.5,
    expectedStatus: '良好'
  },
  {
    name: '天水市麦积区',
    description: '农业区生态环境结构评估',
    params: {
      fragmentation: 0.8,
      cohesion: 85.3,
      diversity: 1.8,
      vulnerability: 25.1
    },
    expectedScore: 88.5,
    expectedStatus: '优秀'
  },
  {
    name: '天水市清水县',
    description: '山区生态环境结构评估',
    params: {
      fragmentation: 0.3,
      cohesion: 92.1,
      diversity: 2.3,
      vulnerability: 15.8
    },
    expectedScore: 95.5,
    expectedStatus: '优秀'
  }
]

// 生态环境胁迫指数示例数据
export const stressIndexExamples = [
  {
    name: '天水市秦州区',
    description: '城市建成区生态环境胁迫评估',
    params: {
      soilErosion: 15.2,
      unusedLand: 8.5,
      cultivatedLand: 35.2,
      constructionLand: 25.8,
      landDegradation: 18.5
    },
    expectedScore: 72.0,
    expectedStatus: '良好'
  },
  {
    name: '天水市麦积区',
    description: '农业区生态环境胁迫评估',
    params: {
      soilErosion: 8.5,
      unusedLand: 12.3,
      cultivatedLand: 42.1,
      constructionLand: 15.2,
      landDegradation: 12.8
    },
    expectedScore: 84.0,
    expectedStatus: '优秀'
  },
  {
    name: '天水市清水县',
    description: '山区生态环境胁迫评估',
    params: {
      soilErosion: 3.2,
      unusedLand: 6.8,
      cultivatedLand: 28.5,
      constructionLand: 8.9,
      landDegradation: 6.2
    },
    expectedScore: 92.0,
    expectedStatus: '优秀'
  }
]

// 生态环境指数计算标准
export const calculationStandards = {
  structure: {
    fragmentation: {
      excellent: { max: 0.5, score: 25, description: '景观破碎化程度很低' },
      good: { max: 1.0, score: 20, description: '景观破碎化程度较低' },
      moderate: { max: 2.0, score: 15, description: '景观破碎化程度中等' },
      poor: { max: 3.0, score: 10, description: '景观破碎化程度较高' },
      critical: { max: Infinity, score: 5, description: '景观破碎化程度很高' }
    },
    cohesion: {
      excellent: { min: 80, score: 25, description: '生态系统连接度很高' },
      good: { min: 60, score: 20, description: '生态系统连接度较高' },
      moderate: { min: 40, score: 15, description: '生态系统连接度中等' },
      poor: { min: 20, score: 10, description: '生态系统连接度较低' },
      critical: { min: 0, score: 5, description: '生态系统连接度很低' }
    },
    diversity: {
      excellent: { min: 1.5, max: 2.5, score: 25, description: '生态多样性适中' },
      good: { min: 1.0, max: 3.0, score: 20, description: '生态多样性良好' },
      moderate: { min: 0.5, max: 3.5, score: 15, description: '生态多样性一般' },
      poor: { min: 0.0, max: 4.0, score: 10, description: '生态多样性较差' },
      critical: { score: 5, description: '生态多样性严重失衡' }
    },
    vulnerability: {
      excellent: { max: 20, score: 25, description: '生态系统脆弱性很低' },
      good: { max: 40, score: 20, description: '生态系统脆弱性较低' },
      moderate: { max: 60, score: 15, description: '生态系统脆弱性中等' },
      poor: { max: 80, score: 10, description: '生态系统脆弱性较高' },
      critical: { max: Infinity, score: 5, description: '生态系统脆弱性很高' }
    }
  },
  stress: {
    soilErosion: {
      excellent: { max: 5, score: 20, description: '土壤侵蚀程度很低' },
      good: { max: 10, score: 16, description: '土壤侵蚀程度较低' },
      moderate: { max: 20, score: 12, description: '土壤侵蚀程度中等' },
      poor: { max: 50, score: 8, description: '土壤侵蚀程度较高' },
      critical: { max: Infinity, score: 4, description: '土壤侵蚀程度很高' }
    },
    unusedLand: {
      excellent: { min: 5, max: 15, score: 20, description: '未利用地比例适中' },
      good: { min: 2, max: 20, score: 16, description: '未利用地比例良好' },
      moderate: { min: 0, max: 25, score: 12, description: '未利用地比例一般' },
      poor: { min: 0, max: 30, score: 8, description: '未利用地比例较高' },
      critical: { score: 4, description: '未利用地比例失衡' }
    },
    cultivatedLand: {
      excellent: { min: 20, max: 40, score: 20, description: '耕地面积比例适中' },
      good: { min: 15, max: 45, score: 16, description: '耕地面积比例良好' },
      moderate: { min: 10, max: 50, score: 12, description: '耕地面积比例一般' },
      poor: { min: 5, max: 55, score: 8, description: '耕地面积比例较高' },
      critical: { score: 4, description: '耕地面积比例失衡' }
    },
    constructionLand: {
      excellent: { max: 10, score: 20, description: '建设用地比例很低' },
      good: { max: 20, score: 16, description: '建设用地比例较低' },
      moderate: { max: 30, score: 12, description: '建设用地比例中等' },
      poor: { max: 40, score: 8, description: '建设用地比例较高' },
      critical: { max: Infinity, score: 4, description: '建设用地比例很高' }
    },
    landDegradation: {
      excellent: { max: 10, score: 20, description: '土地退化程度很低' },
      good: { max: 20, score: 16, description: '土地退化程度较低' },
      moderate: { max: 30, score: 12, description: '土地退化程度中等' },
      poor: { max: 40, score: 8, description: '土地退化程度较高' },
      critical: { max: Infinity, score: 4, description: '土地退化程度很高' }
    }
  }
}

// 建议措施模板
export const suggestionTemplates = {
  structure: {
    fragmentation: {
      high: '建议加强生态廊道建设，减少景观破碎化，提高生态系统连通性',
      medium: '建议适度优化土地利用结构，减少不必要的景观分割',
      low: '当前景观破碎化程度较低，建议继续保持'
    },
    cohesion: {
      low: '建议增加生态连接度，建设生态廊道，提高生态系统内聚力',
      medium: '建议加强生态网络建设，提高生态系统整体性',
      high: '当前生态系统连接度良好，建议继续保持'
    },
    diversity: {
      low: '建议优化土地利用结构，增加生态多样性，保持适度的生态复杂性',
      high: '建议控制过度开发，保持适度的生态多样性',
      optimal: '当前生态多样性适中，建议继续保持'
    },
    vulnerability: {
      high: '建议加强生态保护措施，降低生态系统脆弱性，提高生态稳定性',
      medium: '建议采取预防性保护措施，降低生态系统风险',
      low: '当前生态系统稳定性良好，建议继续保持'
    }
  },
  stress: {
    soilErosion: {
      high: '建议加强水土保持措施，建设防护林，减少土壤侵蚀',
      medium: '建议采取水土保持措施，防止土壤侵蚀加剧',
      low: '当前土壤侵蚀程度较低，建议继续保持'
    },
    unusedLand: {
      high: '建议合理开发利用未利用地，提高土地利用效率',
      medium: '建议适度开发未利用地，平衡保护与利用',
      low: '当前未利用地比例适中，建议继续保持'
    },
    cultivatedLand: {
      high: '建议控制耕地扩张，保护自然生态系统，维持生态平衡',
      medium: '建议优化耕地布局，提高耕地质量',
      low: '当前耕地面积比例适中，建议继续保持'
    },
    constructionLand: {
      high: '建议控制建设用地扩张，保护生态空间，提高土地利用效率',
      medium: '建议优化建设用地布局，减少对生态环境的影响',
      low: '当前建设用地比例适中，建议继续保持'
    },
    landDegradation: {
      high: '建议加强土地整治和生态修复，防止土地退化，提高土地质量',
      medium: '建议采取土地保护措施，防止土地退化加剧',
      low: '当前土地质量良好，建议继续保持'
    }
  }
}

// 导出所有数据
export default {
  structureIndexExamples,
  stressIndexExamples,
  calculationStandards,
  suggestionTemplates
}
